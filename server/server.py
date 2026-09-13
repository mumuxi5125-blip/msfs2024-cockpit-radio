# -*- coding: utf-8 -*-
"""
Cockpit Radio Server (v3)
=========================================================
MSFS 2024 驾驶舱电台广播 —— 本地服务端

v3 = v2（去 nircmd）+ 补回 v1 的两处修复 + 修事件循环阻塞
----------------------------------------------------------
相对 v2 的改动：
1. [回归修复] on_quit 退出前调用 stop_ffplay()，否则 ffplay 变孤儿进程继续播放
2. [回归修复] 启动时 cleanup_orphan_ffplay() 清理上次异常退出残留的 ffplay
3. [修复] 音量/停止等可能阻塞的调用改到线程池（asyncio.to_thread），
   不再卡住 websocket 事件循环（v2 的 time.sleep 重试会阻塞最多 2 秒）
4. [健壮性] stop_ffplay 先杀自己的 PID，再按进程名兜底清理

v2 已具备（保留）：
- 音量：pycaw（Windows Core Audio 会话），不再依赖 nircmd.exe
- 停止：psutil 优先 + taskkill 兜底
- 彻底移除 nircmd.exe（VirusTotal 7 家报 PUA/Riskware/Trojan 的元凶）
- 无硬编码开发机路径：程序目录 -> PATH -> 环境变量 FFPLAY_PATH
- ffplay 拉流禁用系统代理 + 浏览器 UA（qtfm 源必需，否则 FM 无声）

依赖（requirements.txt）
------------------------
    websockets>=12
    psutil>=5.9
    pycaw>=20240210
    comtypes>=1.2.0
    pystray>=0.19
    pillow>=10

打包建议（onedir 误报显著低于 onefile，切勿用 UPX）
---------------------------------------------------
    pyinstaller --onedir --noconsole --name CockpitRadioServer server.py
    ffplay.exe / icon.png 放到程序目录；nircmd.exe 不要带。
"""

import asyncio
import ctypes
import json
import logging
import os
import subprocess
import sys
import threading
import time
import winsound

import websockets
from http.server import HTTPServer, SimpleHTTPRequestHandler

VERSION = '1.1.0'

# ---- 可选依赖：托盘 ----
# 显式指定 pystray 后端：冻结/编译后 pystray 自动探测后端容易失败（找不到 win32 后端时
# 会导入 Xorg/AppIndicator 而报错），锁死 win32。
os.environ.setdefault('PYSTRAY_BACKEND', 'win32')
try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except Exception:
    HAS_TRAY = False

# ---- 可选依赖：音量控制（pycaw） ----
try:
    from pycaw.pycaw import AudioUtilities
    HAS_PYCAW = True
except Exception:
    HAS_PYCAW = False

# ---- 可选依赖：进程管理（psutil） ----
try:
    import psutil
    HAS_PSUTIL = True
except Exception:
    HAS_PSUTIL = False


# ================= 路径与常量 =================

def _app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = _app_dir()
BASE = APP_DIR                       # 静态资源目录（preview.html / stations.js 等）
WS_PORT = 8765                       # 面板 WebSocket 端口
HTTP_PORT = 8766                     # 本地预览页端口
LOG_FILE = os.path.join(APP_DIR, 'cockpit.log')
FFPLAY_LOG = os.path.join(APP_DIR, 'ffplay.log')   # ffplay 的 stderr（排查无声问题用）

TARGET_PROC = 'ffplay.exe'           # 被控音频进程
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
      'AppleWebKit/537.36 Chrome/120.0 Safari/537.36')

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)

# 端口探测/非 WebSocket 连接会让 websockets 库往日志里写一大段 Traceback，
# 玩家看到会以为程序出错。这里静音该库的日志。
logging.getLogger('websockets').setLevel(logging.CRITICAL)
logging.getLogger('asyncio').setLevel(logging.CRITICAL)


def log(msg):
    # 无控制台打包（--noconsole / --windows-console-mode=disable）时 sys.stdout 为 None，
    # 直接 print 会抛 AttributeError，故做保护。
    try:
        if sys.stdout is not None:
            print(msg)
    except Exception:
        pass
    logging.info(msg)


# ================= 全局状态 =================

PANEL = None            # 当前面板 WebSocket 连接
FFPLAY_PROC = None      # ffplay 子进程句柄
CUR_VOLUME = 80         # 当前音量 0-100
LAST_URL = None         # 当前播放的流地址（无 pycaw 时用于重启应用音量）
_vol_timer = None       # 音量 debounce 定时器
_FFPLAY_ERR = None      # ffplay stderr 文件句柄


# ================= HTTP：本地预览页 =================

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def run_http():
    os.chdir(BASE)
    srv = HTTPServer(('127.0.0.1', HTTP_PORT), QuietHandler)
    srv.serve_forever()


# ================= 定位外部程序 =================

def find_ffplay():
    """程序目录 -> PATH -> 环境变量 FFPLAY_PATH -> None"""
    local = os.path.join(BASE, 'ffplay.exe')
    if os.path.exists(local):
        return local

    for d in os.environ.get('PATH', '').split(os.pathsep):
        p = os.path.join(d, 'ffplay.exe')
        if os.path.exists(p):
            return p

    env = os.environ.get('FFPLAY_PATH', '')
    if env and os.path.exists(env):
        return env

    return None


# ================= 播放控制 =================

def _watch_ffplay(proc):
    """ffplay 若在 2 秒内异常退出，把它的 stderr 转记到 cockpit.log，
    这样玩家反馈『没声音』时日志里就有真实原因（原先错误被丢进 DEVNULL）。"""
    try:
        rc = proc.wait(timeout=2)
    except Exception:
        return  # 仍在播放，正常
    err = ''
    try:
        if _FFPLAY_ERR is not None and getattr(_FFPLAY_ERR, 'name', None):
            with open(_FFPLAY_ERR.name, 'r', encoding='utf-8', errors='replace') as f:
                err = f.read().strip()
    except Exception:
        pass
    log('[WARN] ffplay exited early rc=%s %s' % (rc, ('| ' + err.replace('\n', ' ')[:300]) if err else ''))


def start_ffplay(url):
    """启动 ffplay 播放 url；返回是否成功"""
    global FFPLAY_PROC, LAST_URL, _FFPLAY_ERR

    ffplay = find_ffplay()
    if not ffplay:
        log('[ERROR] ffplay not found (set FFPLAY_PATH or put ffplay.exe next to server)')
        return False

    if url:
        LAST_URL = url

    stop_ffplay()

    args = [
        ffplay,
        '-nodisp',
        '-autoexit',
        '-loglevel', 'warning',      # warning 级别 + 写入 ffplay.log，便于排查无声
        '-http_proxy', ' ',          # 禁用系统代理，qtfm 源必需
        '-headers', 'User-Agent: ' + UA + '\r\n',
        '-volume', str(CUR_VOLUME),
        url,
    ]

    # ffplay 的错误输出写文件（不写 DEVNULL，否则出问题时无从排查）
    if _FFPLAY_ERR is not None:
        try:
            _FFPLAY_ERR.close()
        except Exception:
            pass
        _FFPLAY_ERR = None
    try:
        _FFPLAY_ERR = open(FFPLAY_LOG, 'wb')
    except Exception:
        _FFPLAY_ERR = subprocess.DEVNULL

    try:
        FFPLAY_PROC = subprocess.Popen(
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=_FFPLAY_ERR,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        log('[LOG] ffplay started, pid=%s vol=%d url=%s' % (FFPLAY_PROC.pid, CUR_VOLUME, url))
        threading.Thread(target=_watch_ffplay, args=(FFPLAY_PROC,), daemon=True).start()
        return True
    except Exception as e:
        log('[ERROR] ffplay start fail: %s' % e)
        return False


def _kill_ffplay_by_name():
    """按进程名兜底清理（处理僵死 / 多次启动 / 上次残留）"""
    if HAS_PSUTIL:
        try:
            killed = 0
            for p in psutil.process_iter(['name']):
                try:
                    if (p.info.get('name') or '').lower() == TARGET_PROC:
                        p.kill()
                        killed += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return killed
        except Exception as e:
            log('[WARN] psutil stop fail: %s' % e)

    try:
        subprocess.Popen(
            ['taskkill', '/F', '/IM', TARGET_PROC],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        log('[WARN] taskkill fail: %s' % e)
    return 0


def stop_ffplay():
    """终止 ffplay —— 先杀自己的 PID，再按进程名兜底"""
    global FFPLAY_PROC

    if FFPLAY_PROC is not None:
        try:
            FFPLAY_PROC.terminate()
        except Exception:
            pass
        FFPLAY_PROC = None

    n = _kill_ffplay_by_name()
    if n:
        log('[LOG] ffplay killed x%d' % n)


def cleanup_orphan_ffplay():
    """启动时清理上次异常退出（崩溃/任务管理器结束）遗留的孤儿 ffplay。
    否则会出现「程序已关闭但电台还在响」。"""
    n = _kill_ffplay_by_name()
    if n:
        log('[LOG] cleanup leftover ffplay x%d' % n)


# ================= 音量控制（pycaw） =================

def _find_ffplay_session():
    """在 Windows 音频会话里找 ffplay 的那一路"""
    if not HAS_PYCAW:
        return None
    # pycaw 通过 COM 访问 Core Audio，而 COM 是「按线程」初始化的：
    # 本函数由 asyncio.to_thread 丢到线程池线程里跑，那些线程没调过 CoInitialize，
    # 会抛 "尚未调用 CoInitialize"(-2147221008) 而静默失败（音量看起来没反应）。
    coinit = None
    try:
        import comtypes
        comtypes.CoInitialize()
        coinit = comtypes
    except Exception as e:
        log('[WARN] CoInitialize fail: %s' % e)
    try:
        for s in AudioUtilities.GetAllSessions():
            proc = getattr(s, 'Process', None)
            if proc is None:
                continue
            name = (proc.name() or '').lower()
            if name == TARGET_PROC:
                return s
    except Exception as e:
        log('[WARN] pycaw enumerate fail: %s' % e)
    finally:
        if coinit is not None:
            try:
                coinit.CoUninitialize()
            except Exception:
                pass
    return None


def _restart_for_volume():
    """无 pycaw 时的音量后端：用新的 -volume 值重启 ffplay（约 1 秒断音）"""
    if LAST_URL:
        log('[LOG] restart ffplay to apply volume %d' % CUR_VOLUME)
        start_ffplay(LAST_URL)


def set_ffplay_volume(vol):
    """把 ffplay 音量设为 vol(0-100)。
    优先 pycaw（平滑，不中断）；不可用时回退为重启 ffplay 应用新音量。
    注意：本函数含重试等待，必须在工作线程里调用（见 ws_handler）。"""
    global CUR_VOLUME, _vol_timer
    CUR_VOLUME = max(0, min(100, int(vol)))

    if not HAS_PYCAW:
        # 降级后端：debounce 后重启一次（拖动滑块时不会反复重启）
        if _vol_timer is not None:
            _vol_timer.cancel()
        _vol_timer = threading.Timer(0.7, _restart_for_volume)
        _vol_timer.daemon = True
        _vol_timer.start()
        log('[LOG] volume %d queued (restart backend, pycaw unavailable)' % CUR_VOLUME)
        return True

    sess = _find_ffplay_session()
    if sess is None:
        # ffplay 刚启动时音频会话可能还没建立，稍等重试（最多 2 秒）
        for _ in range(10):
            time.sleep(0.2)
            sess = _find_ffplay_session()
            if sess is not None:
                break

    if sess is None:
        log('[WARN] ffplay audio session not found (vol=%d saved)' % CUR_VOLUME)
        return False

    try:
        sess.SimpleAudioVolume.SetMasterVolume(CUR_VOLUME / 100.0, None)
        log('[LOG] volume -> %d' % CUR_VOLUME)
        return True
    except Exception as e:
        log('[ERROR] set volume fail: %s' % e)
        return False


# ================= WebSocket =================

async def send(ws, obj):
    if not ws:
        return False
    try:
        await ws.send(json.dumps(obj, ensure_ascii=False))
        return True
    except Exception:
        return False


async def ws_handler(ws):
    role = None
    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            if msg.get('role') != 'panel':
                continue

            global PANEL, LAST_URL
            PANEL = ws
            role = 'panel'
            cmd = msg.get('cmd')

            # 播放控制可能阻塞（Popen / 进程枚举 / 音量重试），
            # 一律丢到线程池执行，避免卡住事件循环导致面板无响应。
            if cmd == 'play':
                await asyncio.to_thread(start_ffplay, msg.get('url', ''))
            elif cmd == 'stop':
                await asyncio.to_thread(stop_ffplay)
                LAST_URL = None          # 已停止：音量调整不应再自动恢复播放
                log('[LOG] stop')
            elif cmd == 'volume':
                v = msg.get('v', CUR_VOLUME)
                await asyncio.to_thread(set_ffplay_volume, v)
    except Exception:
        pass
    finally:
        if role == 'panel' and PANEL is ws:
            PANEL = None


# ================= 主循环 =================

async def main():
    log('Cockpit Radio service started (v%s)' % VERSION)
    log('  Panel WS port: %d' % WS_PORT)
    log('  Preview page: http://127.0.0.1:%d/preview.html' % HTTP_PORT)
    log('  ffplay: %s' % (find_ffplay() or 'NOT FOUND'))
    log('  volume backend: %s' % ('pycaw (smooth)' if HAS_PYCAW else 'ffplay restart (install pycaw for smooth volume)'))
    log('  process backend: %s' % ('psutil OK' if HAS_PSUTIL else 'taskkill fallback'))

    async with websockets.serve(ws_handler, '127.0.0.1', WS_PORT):
        await asyncio.Future()


# ================= 托盘 =================

def make_tray_icon():
    ico = os.path.join(APP_DIR, 'icon.png')
    if os.path.exists(ico):
        try:
            im = Image.open(ico).convert('RGBA').resize((48, 48), Image.LANCZOS)
            return im
        except Exception:
            pass

    img = Image.new('RGBA', (48, 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 44, 44], fill=(42, 90, 134, 255))
    d.line([24, 40, 24, 16], fill=(255, 255, 255, 255), width=4)
    d.arc([13, 4, 35, 26], 180, 360, fill=(255, 215, 110, 255), width=4)
    return img


def run_tray():
    def on_quit(icon, item):
        icon.stop()
        # 退出前必须停掉 ffplay，否则它会变成孤儿进程继续播放
        stop_ffplay()
        log('[LOG] quit -> ffplay stopped')
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem('驾驶舱电台 服务运行中', None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('退出', on_quit),
    )
    icon = pystray.Icon('cockpit_radio', make_tray_icon(), '驾驶舱电台', menu)
    icon.run()


# ================= 启动提示 =================

def startup_prompt():
    # 自动化测试/静默场景可设 COCKPIT_SILENT=1 跳过弹窗，否则弹窗会挡住无人值守的测试
    if os.environ.get('COCKPIT_SILENT') == '1':
        log('startup prompt skipped (COCKPIT_SILENT=1)')
        return
    try:
        winsound.MessageBeep(winsound.MB_ICONINFORMATION)
    except Exception:
        pass
    try:
        ctypes.windll.user32.MessageBoxW(
            0,
            '驾驶舱电台服务已启动，已最小化到右下角托盘。\n'
            '现在请启动微软模拟飞行(MSFS2024)，打开面板即可选台收听。\n\n'
            '(在右下角电台图标点右键可退出服务)',
            '驾驶舱电台 Cockpit Radio',
            64,
        )
    except Exception as e:
        log('prompt fail: %s' % e)
    log('startup prompt done')


# ================= 入口 =================

if __name__ == '__main__':
    cleanup_orphan_ffplay()          # 先清掉上次可能残留的孤儿 ffplay

    threading.Thread(target=run_http, daemon=True).start()

    if HAS_TRAY:
        threading.Thread(target=run_tray, daemon=True).start()
        log('tray icon running')
    else:
        log('pystray not available -> running without tray')

    threading.Thread(target=startup_prompt, daemon=True).start()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        stop_ffplay()
        sys.exit(0)
