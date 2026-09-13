# Cockpit Radio — Nuitka 构建脚本
# =========================================================
# 目的：用 Nuitka 取代 PyInstaller，去掉 PyInstaller 引导器特征
#       （CTF/MEIPASS + 运行时解压执行载荷 = 静态 ML 引擎判 "Dropper" 的主因）
#
# 用法：在普通 PowerShell 里直接跑
#       powershell -ExecutionPolicy Bypass -File .\build_nuitka.ps1
#
# 产物：.\dist_nuitka\CockpitRadioServer.dist\CockpitRadioServer.exe
#       脚本会自动把 ffplay.exe / icon.png 拷进去

$ErrorActionPreference = 'Stop'
$src = 'D:\DeepSeek Code\duihua\cockpitradio_v3'
$py  = 'C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe'
$out = Join-Path $src 'dist_nuitka'

Write-Host '=== 0) 准备 MSVC 环境 + 工作区 Python 环境 ===' -ForegroundColor Cyan
# 本机沙箱只允许写工作区，pip 无法装进系统 site-packages，
# 故 Nuitka 及依赖放在 _pyenv，用 PYTHONPATH 引用。
$pyenv = Join-Path $src '_pyenv'
if (-not (Test-Path (Join-Path $pyenv 'nuitka'))) {
    throw "找不到工作区依赖目录: $pyenv （先跑 setup_pyenv.py）"
}
$env:PYTHONPATH = $pyenv
Write-Host "  PYTHONPATH: $pyenv"
# Nuitka 默认缓存目录在 %LOCALAPPDATA%，沙箱不可写 -> 指到工作区
$env:NUITKA_CACHE_DIR = Join-Path $src '..\_tmp\nuitka-cache'
New-Item -ItemType Directory -Force -Path $env:NUITKA_CACHE_DIR | Out-Null
Write-Host "  NUITKA_CACHE_DIR: $env:NUITKA_CACHE_DIR"

$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $vswhere)) { throw 'vswhere 未找到：没装 Visual Studio' }
$vsPath = & $vswhere -latest -products * -property installationPath
if (-not $vsPath) { throw 'vswhere 未返回安装路径' }
$devShell = Join-Path $vsPath 'Common7\Tools\Microsoft.VisualStudio.DevShell.dll'
if (-not (Test-Path $devShell)) { throw "找不到 DevShell.dll: $devShell" }
Import-Module $devShell
Enter-VsDevShell -VsInstallPath $vsPath -SkipAutomaticLocation -DevCmdArguments '-arch=x64 -host_arch=x64' | Out-Null
Write-Host "  VS: $vsPath"
Write-Host "  cl: $((Get-Command cl -ErrorAction SilentlyContinue).Source)"

Write-Host "`n=== 1) 清理旧产物 ===" -ForegroundColor Cyan
foreach ($p in @($out, (Join-Path $src 'CockpitRadioServer.build'), (Join-Path $src 'CockpitRadioServer.onefile-build'))) {
    if (Test-Path $p) { Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue; Write-Host "  删除 $p" }
}
# 清掉可能残留的进程，否则文件被占用会构建失败
Get-Process CockpitRadioServer, ffplay -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "`n=== 2) Nuitka 构建（standalone，无控制台）===" -ForegroundColor Cyan
Push-Location $src
try {
    & $py -m nuitka `
        --standalone `
        --assume-yes-for-downloads `
        --python-flag=-OO `
        --windows-console-mode=disable `
        --include-package=pystray `
        --include-package=websockets `
        --include-package=comtypes `
        --include-package=pycaw `
        --include-module=pystray._win32 `
        --include-module=websockets.asyncio `
        --include-module=websockets.asyncio.server `
        --include-module=websockets.asyncio.client `
        --include-module=websockets.asyncio.connection `
        --include-module=websockets.asyncio.messages `
        --include-module=websockets.legacy `
        --include-module=websockets.legacy.server `
        --include-module=websockets.legacy.client `
        --nofollow-import-to=numpy `
        --nofollow-import-to=more_itertools `
        --nofollow-import-to=comtypes.test `
        --nofollow-import-to=psutil._pslinux `
        --nofollow-import-to=psutil._psbsd `
        --nofollow-import-to=psutil._psosx `
        --nofollow-import-to=psutil._pssunos `
        --company-name="Cockpit Radio (open source, MIT)" `
        --product-name="Cockpit Radio" `
        --file-version=1.1.0.0 `
        --product-version=1.1.0.0 `
        --file-description="Cockpit Radio Server - local audio service for MSFS 2024" `
        --trademarks="MIT License - https://github.com/mumuxi5125-blip/msfs2024-cockpit-radio" `
        --copyright="MIT License. https://github.com/mumuxi5125-blip/msfs2024-cockpit-radio" `
        --output-dir="$out" `
        --remove-output `
        server.py
} finally {
    Pop-Location
}
if ($LASTEXITCODE -ne 0) { throw "Nuitka 构建失败，exit=$LASTEXITCODE" }

Write-Host "`n=== 3) 拷入 ffplay.exe / icon.png ===" -ForegroundColor Cyan
$dist = Join-Path $out 'server.dist'
if (-not (Test-Path $dist)) { throw "找不到产物目录: $dist" }
$ffplaySrc = 'D:\Cockpit radio\CockpitRadio_v1.1.0\CockpitRadioServer\ffplay.exe'
if (-not (Test-Path $ffplaySrc)) { $ffplaySrc = Join-Path $src 'dist\CockpitRadioServer\ffplay.exe' }
Copy-Item $ffplaySrc (Join-Path $dist 'ffplay.exe') -Force
$iconSrc = Join-Path $src 'icon.png'
if (-not (Test-Path $iconSrc)) { $iconSrc = 'D:\Cockpit radio\CockpitRadio_v1.1.0\CockpitRadioServer\icon.png' }
if (Test-Path $iconSrc) { Copy-Item $iconSrc (Join-Path $dist 'icon.png') -Force; Write-Host "  icon.png <- $iconSrc" }
Write-Host "  ffplay.exe <- $ffplaySrc"

Write-Host "`n=== 4) 结果 ===" -ForegroundColor Cyan
# Nuitka 按源文件名输出 server.exe，这里改成发布用的 CockpitRadioServer.exe
$rawExe = Join-Path $dist 'server.exe'
$exe = Join-Path $dist 'CockpitRadioServer.exe'
if ((Test-Path $rawExe) -and -not (Test-Path $exe)) {
    Move-Item $rawExe $exe -Force
    Write-Host "  重命名: server.exe -> CockpitRadioServer.exe"
}
if (-not (Test-Path $exe)) { throw "产物 exe 不存在: $exe" }
Get-Item $exe | Select-Object FullName, @{n='MB';e={[math]::Round($_.Length/1MB,2)}}, LastWriteTime | Format-List
(Get-Item $exe).VersionInfo | Select-Object FileDescription, ProductName, CompanyName, FileVersion, ProductVersion, OriginalFilename, LegalCopyright | Format-List
Get-FileHash $exe -Algorithm SHA256 | Format-List
Write-Host "产物目录: $dist"
