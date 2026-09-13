# Cockpit Radio v1.1.0 — 打包分发包（Nuitka 版）
# =========================================================
# 把 Nuitka 产物与现有的游戏包/说明文档组装成发布用 zip
# 用法：pwsh -NoProfile -File .\pack_release.ps1

$ErrorActionPreference = 'Stop'
$old  = 'D:\Cockpit radio\CockpitRadio_v1.1.0'          # 现有 v1.1.0 分发目录（游戏包/说明）
# 注意：本机沙箱只允许写工作区，所以产物放在工作区内；
#       最后用 -CopyTo 手动拷到 D:\Cockpit radio\
$root = 'D:\DeepSeek Code\duihua\cockpitradio_release'
$new  = Join-Path $root 'CockpitRadio_v1.1.0-nuitka'    # 新分发目录
$dist = 'D:\DeepSeek Code\duihua\cockpitradio_v3\dist_nuitka\server.dist'
$zip  = Join-Path $root 'CockpitRadio_v1.1.0-nuitka.zip'

Write-Host '=== 1) 组装分发目录 ===' -ForegroundColor Cyan
if (Test-Path $new) { Remove-Item $new -Recurse -Force }
New-Item -ItemType Directory -Force -Path $new | Out-Null

# 游戏包（原样复制）
Copy-Item (Join-Path $old 'cockpitradio-cockpitradio') $new -Recurse -Force
Write-Host '  cockpitradio-cockpitradio/ (游戏包)'

# 服务端（Nuitka 产物）
$srvDst = Join-Path $new 'CockpitRadioServer'
New-Item -ItemType Directory -Force -Path $srvDst | Out-Null
Get-ChildItem $dist -File | Where-Object { $_.Name -notin @('cockpit.log', 'ffplay.log') } | ForEach-Object {
    Copy-Item $_.FullName $srvDst -Force
}
Write-Host '  CockpitRadioServer/ (含 CockpitRadioServer.exe + ffplay.exe + 运行时)'

# 安装说明
Copy-Item (Join-Path $old 'README_安装说明.txt') $new -Force
Write-Host '  README_安装说明.txt'

Write-Host "`n=== 2) 校验 ===`n" -ForegroundColor Cyan
$exe = Join-Path $srvDst 'CockpitRadioServer.exe'
foreach ($f in @('CockpitRadioServer.exe', 'ffplay.exe', 'icon.png')) {
    $p = Join-Path $srvDst $f
    if (Test-Path $p) { Write-Host ("  [OK] {0,-26} {1,8} MB" -f $f, [math]::Round((Get-Item $p).Length/1MB, 2)) }
    else { Write-Host "  [缺失] $f" -ForegroundColor Red }
}
Write-Host "  exe SHA256: $((Get-FileHash $exe -Algorithm SHA256).Hash)"
Write-Host "  目录总大小: $([math]::Round((Get-ChildItem $new -Recurse -File | Measure-Object Length -Sum).Sum/1MB,1)) MB"

Write-Host "`n=== 3) 打 zip ===`n" -ForegroundColor Cyan
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $new '*') -DestinationPath $zip -CompressionLevel Optimal
Write-Host "  $zip"
Write-Host "  zip 大小: $([math]::Round((Get-Item $zip).Length/1MB,1)) MB"
Write-Host "  zip SHA256: $((Get-FileHash $zip -Algorithm SHA256).Hash)"
