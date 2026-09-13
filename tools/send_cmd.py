# -*- coding: utf-8 -*-
"""向本地服务发一条指令：play <url> | stop | volume <0-100>"""
import asyncio
import json
import sys

import websockets


async def main():
    if len(sys.argv) < 2:
        print('usage: send_cmd.py play <url> | stop | volume <0-100>')
        return
    c = sys.argv[1]
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    async with websockets.connect('ws://127.0.0.1:8765') as ws:
        if c == 'play':
            msg = {'role': 'panel', 'cmd': 'play', 'url': arg or ''}
        elif c == 'volume':
            msg = {'role': 'panel', 'cmd': 'volume', 'v': int(arg or 50)}
        else:
            msg = {'role': 'panel', 'cmd': c}
        await ws.send(json.dumps(msg))
        await asyncio.sleep(0.4)
    print('sent:', msg)


asyncio.run(main())
