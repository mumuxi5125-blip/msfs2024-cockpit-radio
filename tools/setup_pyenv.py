# -*- coding: utf-8 -*-
"""
把 Nuitka 及其依赖装到工作区目录（不碰系统 site-packages）。

原因：本机沙箱只允许写工作区，pip install 写 %APPDATA%\\Python 会被拒。
做法：直接从 PyPI 下载 wheel，解包到 <workspace>\\_pyenv，用 PYTHONPATH 引用。

用法：
    python setup_pyenv.py            # 下载并解包
    set PYTHONPATH=...\\_pyenv
    python -m nuitka --version
"""
import json
import os
import sys
import urllib.request
import zipfile

PROXY = os.environ.get('HTTPS_PROXY') or 'http://127.0.0.1:7890'
DEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_pyenv')

# 固定版本避免解析器遍历 PyPI 全量 index（Nuitka 有几百个 sdist，走代理会卡死）
PKGS = [
    ('nuitka', None),        # None = 用最新稳定版
    ('ordered-set', None),
    ('zstandard', None),
    ('pycaw', None),
    ('comtypes', None),
]

_opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({'http': PROXY, 'https': PROXY})
)


def get_json(url):
    with _opener.open(url, timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))


def pick_wheel(pkg, version=None):
    """从 PyPI JSON 里挑一个 cp312 win_amd64（或纯 python）的 wheel"""
    url = 'https://pypi.org/pypi/%s/json' % pkg
    if version:
        url = 'https://pypi.org/pypi/%s/%s/json' % (pkg, version)
    data = get_json(url)
    ver = data['info']['version']
    best = None
    for f in data['urls']:
        if f['packagetype'] != 'bdist_wheel':
            continue
        fn = f['filename'].lower()
        if not fn.endswith('.whl'):
            continue
        if 'win_amd64' not in fn and 'none-any' not in fn:
            continue
        if 'cp312' in fn:
            score = 3
        elif 'abi3' in fn or 'cp3' in fn:
            score = 2
        elif 'py3' in fn or 'py2.py3' in fn:
            score = 1
        else:
            continue
        if best is None or score > best[0]:
            best = (score, f['filename'], f['url'], f['size'])
    return ver, best


def install(pkg, version):
    ver, best = pick_wheel(pkg, version)
    if not best:
        print('  [X] %s: 没有可用的 win_amd64/纯 python wheel' % pkg)
        return False
    score, fn, url, size = best
    print('  [>] %-14s %-10s %s (%.2f MB)' % (pkg, ver, fn, size / 1048576))
    tmp = os.path.join(DEST, '_dl_' + fn)
    with _opener.open(url, timeout=120) as r, open(tmp, 'wb') as f:
        while True:
            c = r.read(65536)
            if not c:
                break
            f.write(c)
    with zipfile.ZipFile(tmp) as z:
        z.extractall(DEST)
    os.remove(tmp)
    print('  [OK] 解包完成')
    return True


def main():
    os.makedirs(DEST, exist_ok=True)
    print('目标目录: %s' % DEST)
    print('代理: %s' % PROXY)
    ok = 0
    for pkg, ver in PKGS:
        try:
            if install(pkg, ver):
                ok += 1
        except Exception as e:
            print('  [X] %s 失败: %s: %s' % (pkg, type(e).__name__, e))
    print('\n完成 %d/%d' % (ok, len(PKGS)))
    # 结果自检
    sp = DEST
    for m in ('nuitka', 'ordered_set', 'zstandard', 'pycaw', 'comtypes'):
        p = os.path.join(sp, m)
        print('  %-14s %s' % (m, 'OK' if os.path.exists(p) else 'MISSING'))
    return 0 if ok == len(PKGS) else 1


if __name__ == '__main__':
    sys.exit(main())
