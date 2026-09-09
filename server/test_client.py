# -*- coding: utf-8 -*-
# 命令行测试：python test_client.py <台代码>
# 例子：python test_client.py gdmusic → 播放广东音乐之声
import asyncio
import json
import sys
import websockets

STREAMS = {
    "bbc": "http://stream.live.vc.bbcmedia.co.uk/bbc_world_service",
    "npr": "https://npr-ice.streamguys1.com/live.mp3",
    "kexp": "https://kexp-mp3-128.streamguys1.com/kexp128.mp3",
    "gdmusic": "https://lhttp.qtfm.cn/live/1260/64k.mp3",
    "yctx": "https://lhttp.qtfm.cn/live/1262/64k.mp3",
    "mmjt": "https://lhttp.qingting.fm/live/20211574/64k.mp3",
    "lgzs": "https://lhttp.qtfm.cn/live/20500149/64k.mp3",
    "asiafm": "https://lhttp.qtfm.cn/live/15318569/64k.mp3",
    "cnr1": "https://lhttp.qtfm.cn/live/15318317/64k.mp3",
    "ycj": "http://lhttp.qingting.fm/live/276/64k.mp3",
    "shxw": "http://lhttp.qingting.fm/live/270/64k.mp3",
    "bjxw": "https://lhttp.qtfm.cn/live/339/64k.mp3",
    "rfi": "https://rfienchinois64k.ice.infomaniak.ch//rfienchinois-64.mp3",
    "jsjd": "https://lhttp.qtfm.cn/live/4938/64k.mp3",
    "twgd": "http://59.120.88.155:8000/live.mp3",
    "zgpop": "https://n03.rcs.revma.com/aw9uqyxy2tzuv",
    "hygd": "https://radio.chinesemusicworld.com/chinesemusic.mp3",
    "vhhh_twr": "https://www.liveatc.net/hlisten.php?mount=vhhh_twr&icao=vhhh",
    "rjtt_control": "https://www.liveatc.net/hlisten.php?mount=rjtt_control&icao=rjtt",
    "llbg2": "https://www.liveatc.net/hlisten.php?mount=llbg2&icao=llbg"
}

NAMES = {
    "bbc": "BBC环球", "npr": "NPR", "kexp": "KEXP",
    "gdmusic": "广东音乐之声", "yctx": "羊城交通电台", "mmjt": "茂名交通",
    "lgzs": "两广之声", "asiafm": "AsiaFM粤语台", "cnr1": "中国之声",
    "ycj": "第一财经", "shxw": "上海新闻广播", "bjxw": "北京新闻广播",
    "rfi": "RFI中文", "jsjd": "江苏经典流行", "twgd": "台湾古典97.7",
    "zgpop": "中广流行网", "hygd": "华语古典音乐",
    "vhhh_twr": "香港塔台", "rjtt_control": "东京区调", "llbg2": "LLBG塔台"
}


async def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "play"
    async with websockets.connect("ws://127.0.0.1:8765") as ws:
        if arg == "stop":
            await ws.send(json.dumps({"role": "panel", "cmd": "stop"}))
            print("STOP sent")
        elif arg == "list":
            for k in STREAMS:
                print(" ", k, "-", NAMES.get(k, k))
        else:
            url = STREAMS.get(arg, STREAMS["bbc"])
            await ws.send(json.dumps({"role": "panel", "cmd": "play",
                                      "url": url, "name": NAMES.get(arg, arg)}))
            print("PLAY sent:", NAMES.get(arg, arg), "->", url)
            print("ffplay will play it directly (3-10s buffering)")


asyncio.run(main())
