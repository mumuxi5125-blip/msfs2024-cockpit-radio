# Cockpit Radio — MSFS 2024 驾驶舱电台

飞行中听真实 **FM 电台**和**实况 ATC（空管）**的免费插件。游戏工具栏面板选台，本地 ffplay 出声，无需浏览器。

⬇️ 下载：**[Releases](https://github.com/mumuxi5125-blip/msfs2024-cockpit-radio/releases)**

## 安装（3 步）

1. 把 `cockpitradio-cockpitradio` 文件夹放进 MSFS 的 **Community** 文件夹
2. 双击运行 `CockpitRadioServer.exe`（右下角托盘出现图标）
3. 进游戏，从工具栏打开「驾驶舱电台」，点台收听

> ⚠️ 第 2 步的 exe 是出声引擎，**必须先运行再进游戏**，否则没声音。免安装、免 Python。

## 关于杀软提示

服务端是开源的 Python 程序，用 [Nuitka](https://nuitka.net/) 编译成原生 exe，**未做代码签名**，
所以少数安全引擎可能给出"不确定 / 可疑"这类启发式提示。这是所有未签名免费软件的常见情况。

源码在 `server/` 目录可自行审阅，也可用 `tools/build_nuitka.ps1` 自行编译。
如遇拦截，把 `CockpitRadioServer` 文件夹加入信任即可。

## 构建（自行编译）

```powershell
cd tools
pwsh -File .\build_nuitka.ps1     # 需要 Python 3.12 + Visual Studio 2022 (C++ 工具链)
pwsh -File .\test_nuitka.ps1      # 7 项端到端验证
```

## 特性

- 🎧 FM：广州/全国/港澳台/海外（BBC、NPR 等）
- ✈️ ATC：香港 VHHH、新加坡樟宜 WSSS（无人通话时静默属正常）
- 🎚️ 面板内置音量与停止

MIT License © mumuxi5125-blip
