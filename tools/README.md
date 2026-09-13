# 构建与打包

这些脚本用来把 `server/server.py` 编译成可分发的原生 exe，并组装发布包。

## 为什么用 Nuitka 而不是 PyInstaller

PyInstaller 的引导器（自解压 + 运行时执行载荷 + 无签名 + 无版本信息）会被静态 ML 引擎
判成 `BehavesLike.Win64.Dropper` / `Static AI - Suspicious PE`，导致平台（flightsim.to 等）
审核不通过。Nuitka 把 Python 直接编译成 C 再编译成机器码，没有引导器特征，误报显著更少。

| | PyInstaller | Nuitka |
|---|---|---|
| exe 大小 | 5.7 MB | 19.2 MB |
| 运行时自解压载荷 | 有 | 无 |
| Windows 版本信息 | 无 | 完整 |

## 前置要求

- Python 3.12
- Visual Studio 2022（含 C++ 工具链，`cl.exe`）
- Nuitka 4.2.1 + `ordered-set` / `zstandard` 等依赖

如果 `pip install` 无法写入系统目录（沙箱/权限受限环境），用 `setup_pyenv.py`
把依赖装到工作区的 `_pyenv` 目录，构建脚本会用 `PYTHONPATH` 引用它：

```powershell
python setup_pyenv.py
```

## 构建

```powershell
pwsh -File .\build_nuitka.ps1
```

产物：`cockpitradio_v3\dist_nuitka\server.dist\CockpitRadioServer.exe`

脚本会自动：
- 初始化 MSVC 环境（`vswhere` + `Enter-VsDevShell`）
- 设置 `NUITKA_CACHE_DIR` 到可写目录（默认在 `%LOCALAPPDATA%`，受限环境会失败）
- 剥离 docstring（`--python-flag=-OO`）——避免源码注释里的敏感词（例如已移除的
  `nircmd.exe` 相关说明）被编译进二进制、给静态扫描器留下误导性字符串
- 排除用不到的依赖（`numpy` / `more_itertools` / `comtypes.test` / 非 Windows 的
  `psutil._ps*`），exe 从 38 MB 降到 19 MB
- 重命名 `server.exe` → `CockpitRadioServer.exe`，并拷入 `ffplay.exe` / `icon.png`

## 验证

```powershell
pwsh -File .\test_nuitka.ps1
```

覆盖：起服务 / play 拉起 ffplay 并持续播放 / 音量生效 / stop 杀掉 ffplay /
启动时清理孤儿 ffplay / 托盘正常 / 日志无错误。

测试依赖 `send_cmd.py`（WebSocket 发指令）和 `test120s.wav`（测试音频，在
`cockpitradio_v3` 目录）。

## 打包发布

```powershell
pwsh -File .\pack_release.ps1
```

把构建产物与游戏包、安装说明组装成 zip。产品放在工作区（受限环境无法直接写
`D:\Cockpit radio\`），需要手动拷贝。

## 已知的坑（都已在脚本里处理）

| 坑 | 现象 | 处理 |
|---|---|---|
| `--enable-plugin=pystray` | `unknown plug-in 'pystray'` | Nuitka 4.2.1 没有该插件，用 `--include-package` |
| `--windows-version-info` | `no such option` | 该版本无此选项，改用零散参数 |
| `websockets` 15 惰性导入 | 启动即崩：`No module named 'websockets.asyncio'` | `--include-package=websockets` + 显式 `--include-module` |
| 无控制台打包 | `print()` 遇 `sys.stdout is None` 抛异常 | `server.py` 里已做保护 |
| 沙箱下 `NUITKA_CACHE_DIR` | `failed to create cache directory` | 脚本指向工作区 |
| 首次编译慢 | 420+ 个 C 文件、最大单个 8.9 MB，约 10 分钟 | 有 clcache，二次重编约 1 分钟 |
