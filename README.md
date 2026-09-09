# Cockpit Radio — Live FM & ATC Radio for MSFS 2024

驾驶舱电台 — 为 Microsoft Flight Simulator 2024 飞行中收听真实 FM 电台与实况空管频率 (ATC) 的免费插件。

Listen to real live FM radio and real aviation ATC feeds while you fly MSFS 2024 — no external browser needed. Audio is streamed by a bundled ffplay engine controlled from an in-game toolbar panel.

> ⬇️ **Download**: grab the latest zip from the [Releases](https://github.com/REPLACE_OWNER/msfs2024-cockpit-radio/releases) page.
> ⬇️ **下载**：请到 Releases 页面下载最新 zip。

---

## Features / 功能

- 🎧 **FM radio** — real music/news stations covering Guangzhou, mainland China, Hong Kong / Macau / Taiwan, and overseas (BBC, NPR, KEXP and more).
- ✈️ **Live ATC** — real air-traffic-control feeds (currently Hong Kong Chek Lap Kok **VHHH** and Singapore Changi **WSSS**).
- 🎚️ **Volume & Stop** built right into the panel; clean channel switching, no browser, no sim-rate hack.

## Screenshots / 截图

*(add your screenshots here)*

---

## Installation / 安装

> ⚠️ **IMPORTANT**: the `.exe` is the audio engine. **You must run it before starting the sim, otherwise there is no sound.**

1. Copy the folder **`cockpitradio-cockpitradio`** into your MSFS **Community** folder.
2. Open the **`CockpitRadioServer`** folder and **double-click `CockpitRadioServer.exe`** — it minimises to the system tray (click OK on the popup).
3. Launch MSFS 2024, open the **Cockpit Radio** panel from the top toolbar, and click a station (FM or ATC).

The `.exe` requires no installation and no Python. If your antivirus flags it, please add it to trusted applications.

---

## How it works / 工作原理

```
In-game panel / preview page  --ws 127.0.0.1:8765-->  server.py  -->  ffplay.exe (audio out)
                                              volume -->  nircmd.exe setappvolume ffplay.exe
```

- The in-game `html_ui` panel is **UI only** — it sends commands over websocket to the local `server.py`.
- Audio is produced by **ffplay** (bundled), because MSFS 2024's in-game WebUI (Coherent GT) has **no audio output**.
- The service runs as `CockpitRadioServer.exe` (PyInstaller build, Python not required) with a system-tray icon and a startup popup.

### Source layout / 源码结构

```
server/   – Python websocket service + preview page (browser test panel)
panel/    – MSFS 2024 in-game toolbar panel sources (PackageSources)
```

## Adding stations / 加台方法

- FM stations use direct MP3 links, mostly `https://lhttp.qtfm.cn/live/{id}/64k.mp3`. Find the id on a `qtfm.cn/radios/{id}` page, then verify the MP3 plays.
- ATC feeds use direct `https://{relay}.liveatc.net/{mount}` MP3 links (relay/mount can be found in the feed page source under `STREAM_URLS=[...]`). ATC silence is normal when nobody is talking.
- Edit `server/stations.js` (server side) or the inlined station list in `panel/html_ui/InGamePanels/CockpitRadio/preview.js` (game panel side — note Coherent GT does not share `const` across `<script>` tags, keep the data inlined as `var`).

## Building the exe / 打包后端

```bash
cd server
pip install pyinstaller pystray pillow websockets
python -m PyInstaller --onefile --windowed --name CockpitRadioServer server.py
```

Place `ffplay.exe` and `nircmd.exe` next to the built exe (or anywhere on PATH). `server.py` looks for them next to the exe first, then on PATH, then a dev fallback path.

## License / 许可证

MIT — see [LICENSE](LICENSE).

Made with 🎧 by Haha. If you enjoy it, leave a like on [Flightsim.to](https://flightsim.to).
