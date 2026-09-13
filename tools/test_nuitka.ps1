# Cockpit Radio — Nuitka 构建产物验证脚本
# =========================================================
# 验证内容（与 v3 的 test6.ps1 一致）：
#   1) 服务能起来
#   2) play 能拉起 ffplay 并持续播放
#   3) volume 能生效
#   4) stop 能杀掉 ffplay
#   5) 启动时能清理残留 ffplay
#   6) ffplay.log / cockpit.log 无错误
#
# 用法：pwsh -NoProfile -File .\test_nuitka.ps1

$ErrorActionPreference = 'Continue'
$pyenv = 'D:\DeepSeek Code\duihua\cockpitradio_v3\_pyenv'
$v3    = 'D:\DeepSeek Code\duihua\cockpitradio_v3'
$d     = Join-Path $v3 'dist_nuitka\server.dist'
$exe   = Join-Path $d 'CockpitRadioServer.exe'
$log   = Join-Path $d 'cockpit.log'
$send  = Join-Path $v3 'send_cmd.py'

$env:PYTHONPATH = $pyenv
$env:PYTHONIOENCODING = 'utf-8'
$env:COCKPIT_SILENT = '1'      # 跳过启动弹窗
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if (-not (Test-Path $exe)) { Write-Host "找不到 exe: $exe" -ForegroundColor Red; exit 1 }
Write-Host "exe: $exe"

Write-Host "`n=== 0) 清理旧进程/日志 ===" -ForegroundColor Cyan
Get-Process ffplay, CockpitRadioServer -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep 1
Remove-Item $log, (Join-Path $d 'ffplay.log') -ErrorAction SilentlyContinue

Write-Host "`n=== 1) 起本地 HTTP 音频服务(8899) ===" -ForegroundColor Cyan
$http = Start-Process python -ArgumentList '-m','http.server','8899','--bind','127.0.0.1' -WorkingDirectory $v3 -PassThru -WindowStyle Hidden
Start-Sleep 3
Write-Host "http server alive=$(-not $http.HasExited)"

Write-Host "`n=== 2) 起 Nuitka 服务 ===" -ForegroundColor Cyan
$srv = Start-Process $exe -WorkingDirectory $d -PassThru
Start-Sleep 6
Write-Host "server alive=$(-not $srv.HasExited)"
if ($srv.HasExited) { Write-Host "服务启动即退出，exit=$($srv.ExitCode)" -ForegroundColor Red; exit 1 }

Write-Host "`n=== 3) play + 采样 ffplay ===" -ForegroundColor Cyan
python $send play 'http://127.0.0.1:8899/test120s.wav'
$pidsSeen = @()
for ($i = 0; $i -lt 8; $i++) {
    $pids = ((Get-Process ffplay -ErrorAction SilentlyContinue).Id) -join ','
    if ($pids) { $pidsSeen += $pids }
    Write-Host ("t={0,2}s  ffplay=[{1}]" -f $i, $pids)
    Start-Sleep 1
}
Write-Host "播放采样: $(if($pidsSeen.Count -ge 6){'OK ffplay 持续存活'}else{'FAIL ffplay 未持续存活'})"

Write-Host "`n=== 4) 调音量 30 ===" -ForegroundColor Cyan
python $send volume 30
Start-Sleep 3
$vf = ((Get-Process ffplay -ErrorAction SilentlyContinue).Id) -join ','
Write-Host "调音量后 ffplay=[$vf]"

Write-Host "`n=== 5) stop ===" -ForegroundColor Cyan
python $send stop
Start-Sleep 3
$left = ((Get-Process ffplay -ErrorAction SilentlyContinue).Id) -join ','
Write-Host "stop 后 ffplay=[$left]  => $(if(-not $left){'OK 已停止'}else{'FAIL'})"

Write-Host "`n=== 6) 残留清理验证 ===" -ForegroundColor Cyan
# 手动拉起一个孤儿 ffplay，重启服务看能否清掉
$orphan = Start-Process (Join-Path $d 'ffplay.exe') -ArgumentList '-nodisp','-autoexit',"http://127.0.0.1:8899/test120s.wav" -PassThru -WindowStyle Hidden
Start-Sleep 2
Write-Host "孤儿 ffplay pid=$($orphan.Id) alive=$(-not $orphan.HasExited)"
Get-Process CockpitRadioServer -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 2
$srv2 = Start-Process $exe -WorkingDirectory $d -PassThru
Start-Sleep 6
$orphanAlive = Get-Process -Id $orphan.Id -ErrorAction SilentlyContinue
Write-Host "重启后孤儿 ffplay: $(if($orphanAlive){'FAIL 仍存活'}else{'OK 已被清理'})"

Write-Host "`n=== 7) 日志 ===" -ForegroundColor Cyan
if (Test-Path $log) { Get-Content $log | Select-Object -Last 14 } else { Write-Host '(无 cockpit.log)' -ForegroundColor Red }
Write-Host "--- ffplay.log ---"
$fl = Join-Path $d 'ffplay.log'
if (Test-Path $fl) { $c = Get-Content $fl -Raw; if ($c) { $c } else { '(空 —— 无错误)' } } else { '(无)' }

Write-Host "`n=== 8) 清理 ===" -ForegroundColor Cyan
Get-Process ffplay, CockpitRadioServer -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Stop-Process -Id $http.Id -Force -ErrorAction SilentlyContinue
Start-Sleep 1
Write-Host "剩余 ffplay=$((Get-Process ffplay -ErrorAction SilentlyContinue | Measure-Object).Count)"
