# -*- coding: utf-8 -*-
# Cockpit Radio 本地播放服务
# 作用：接收游戏面板命令，用 ffplay 直接出声（声音走系统声卡），
#       nircmd 调进程音量；http 服务仅供 preview.html 预览面板使用。
import asyncio
import ctypes
import json
import logging
import os
import subprocess
import sys
import threading
import winsound
import websockets
from http.server import HTTPServer, SimpleHTTPRequestHandler

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except Exception:
    HAS_TRAY = False

APP_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
BASE = APP_DIR
# 兼容旧引用，全项目统一用 APP_DIR
WS_PORT = 8765     # 面板 <-> 服务 通信
HTTP_PORT = 8766   # preview.html 静态页
LOG_FILE = os.path.join(APP_DIR, "cockpit.log")
# 开发机兜底路径（分发时对方机器没有，会回退到 PATH）
DEV_FFPLAY = r"E:\app\Downvideos\ffmpeg\bin\ffplay.exe"

logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")


def log(msg):
    print(msg)
    logging.info(msg)

PANEL = None          # 当前面板连接
FFPLAY_PROC = None    # 当前 ffplay 子进程
CUR_VOLUME = 80       # 当前音量（0-100），切台时复用


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def run_http():
    os.chdir(BASE)
    srv = HTTPServer(("127.0.0.1", HTTP_PORT), QuietHandler)
    srv.serve_forever()


def find_ffplay():
    local = os.path.join(BASE, "ffplay.exe")
    if os.path.exists(local):
        return local
    for d in os.environ.get("PATH", "").split(os.pathsep):
        p = os.path.join(d, "ffplay.exe")
        if os.path.exists(p):
            return p
    if os.path.exists(DEV_FFPLAY):
        return DEV_FFPLAY
    return None


def find_nircmd():
    local = os.path.join(BASE, "nircmd.exe")
    if os.path.exists(local):
        return local
    for d in os.environ.get("PATH", "").split(os.pathsep):
        p = os.path.join(d, "nircmd.exe")
        if os.path.exists(p):
            return p
    return None


def start_ffplay(url):
    global FFPLAY_PROC, CUR_VOLUME
    ffplay = find_ffplay()
    if not ffplay:
        return False
    stop_ffplay()
    # -http_proxy "" 禁用系统代理（qtfm 等源拒绝代理请求）; -headers 带浏览器 UA 绕过防盗链
    args = [ffplay, "-nodisp", "-autoexit", "-loglevel", "error",
            "-http_proxy", " ",
            "-headers", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36\r\n",
            "-volume", str(CUR_VOLUME), url]
    try:
        FFPLAY_PROC = subprocess.Popen(args, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
        log("[LOG] ffplay started, vol=%d" % CUR_VOLUME)
        return True
    except Exception as e:
        log("[ERROR] ffplay start fail: %s" % e)
        return False


def stop_ffplay():
    global FFPLAY_PROC
    if FFPLAY_PROC is not None:
        try:
            FFPLAY_PROC.terminate()
        except Exception:
            pass
        FFPLAY_PROC = None
    nircmd = find_nircmd()
    if nircmd:
        try:
            subprocess.Popen([nircmd, "killprocess", "ffplay.exe"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            pass


def set_ffplay_volume(vol):
    global CUR_VOLUME
    CUR_VOLUME = max(0, min(100, int(vol)))
    nircmd = find_nircmd()
    if not nircmd:
        return False
    level = CUR_VOLUME / 100.0
    try:
        subprocess.Popen([nircmd, "setappvolume", "ffplay.exe", ("%.2f" % level)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=subprocess.CREATE_NO_WINDOW)
        return True
    except Exception:
        return False


async def send(ws, obj):
    if ws:
        try:
            await ws.send(json.dumps(obj, ensure_ascii=False))
            return True
        except Exception:
            pass
    return False


async def ws_handler(ws):
    global PANEL
    role = None
    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            if msg.get("role") == "panel":
                PANEL = ws
                role = "panel"
                cmd = msg.get("cmd")
                if cmd == "play":
                    start_ffplay(msg.get("url", ""))
                elif cmd == "stop":
                    stop_ffplay()
                    log("[LOG] stop")
                elif cmd == "volume":
                    v = msg.get("v", CUR_VOLUME)
                    set_ffplay_volume(v)
                    log("[LOG] volume %s" % v)
    finally:
        if role == "panel" and PANEL is ws:
            PANEL = None


async def main():
    log("Cockpit Radio service started")
    log("  Panel WS port: %d" % WS_PORT)
    log("  Preview page: http://127.0.0.1:%d/preview.html" % HTTP_PORT)
    log("  ffplay: %s" % (find_ffplay() or "NOT FOUND"))
    log("  nircmd: %s" % (find_nircmd() or "NOT FOUND (volume disabled)"))
    async with websockets.serve(ws_handler, "127.0.0.1", WS_PORT):
        await asyncio.Future()  # 永久运行


def make_tray_icon():
    # 优先用 exe 同目录的 icon.png（与游戏工具栏同图），找不到才退回内置手绘
    ico = os.path.join(APP_DIR, "icon.png")
    if os.path.exists(ico):
        try:
            im = Image.open(ico).convert("RGBA").resize((48, 48), Image.LANCZOS)
            return im
        except Exception:
            pass
    img = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 44, 44], fill=(42, 90, 134, 255))
    d.line([24, 40, 24, 16], fill=(255, 255, 255, 255), width=4)
    d.arc([13, 4, 35, 26], start=180, end=360, fill=(255, 215, 110, 255), width=4)
    return img


def cleanup_orphan_ffplay():
    """启动时清理上次异常退出遗留的孤儿 ffplay（防止退出服务/游戏后仍在播）。
    用 nircmd 按进程名清理（本插件的 ffplay 均由此服务或 test 脚本启动）。"""
    nircmd = find_nircmd()
    if not nircmd:
        return
    try:
        subprocess.Popen([nircmd, "killprocess", "ffplay.exe"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=subprocess.CREATE_NO_WINDOW)
        log("[LOG] cleanup leftover ffplay")
    except Exception:
        pass


def run_tray():
    def on_quit(icon, item):
        icon.stop()
        stop_ffplay()   # 退出前停掉 ffplay，否则它会变孤儿进程继续播放
        os._exit(0)
    menu = pystray.Menu(
        pystray.MenuItem("驾驶舱电台 服务运行中", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", on_quit),
    )
    icon = pystray.Icon("cockpit_radio", make_tray_icon(), "驾驶舱电台", menu)
    icon.run()


def startup_prompt():
    """每次双击 exe 启动弹一次提示框+系统提示音。独立线程跑，不阻塞服务。"""
    try:
        winsound.MessageBeep(winsound.MB_ICONINFORMATION)
    except Exception:
        pass
    try:
        ctypes.windll.user32.MessageBoxW(
            0,
            "驾驶舱电台服务已启动，已最小化到右下角托盘。\n"
            "现在请启动微软模拟飞行(MSFS2024)，打开面板即可选台收听。\n\n"
            "(在右下角电台图标点右键可退出服务)",
            "驾驶舱电台 Cockpit Radio",
            0x40)  # MB_ICONINFORMATION
    except Exception as e:
        log("prompt fail: %s" % e)
    log("startup prompt done")


if __name__ == "__main__":
    cleanup_orphan_ffplay()   # 启动先清掉上次可能残留的孤儿 ffplay
    threading.Thread(target=run_http, daemon=True).start()
    if HAS_TRAY:
        threading.Thread(target=run_tray, daemon=True).start()
        log("tray icon running")
    else:
        log("pystray not available -> running without tray")
    threading.Thread(target=startup_prompt, daemon=True).start()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
