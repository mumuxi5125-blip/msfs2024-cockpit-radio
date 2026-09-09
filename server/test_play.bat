@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==========================================
echo 驾驶舱电台 - 出声测试
echo 正在播放：广州青少年广播 FM88.0
echo 听得到声音 = 出声链路正常
echo （关这个窗口或按 Ctrl+C 停止）
echo ==========================================
echo.
ffplay.exe -nodisp -loglevel error -volume 80 "https://lhttp.qtfm.cn/live/20194/64k.mp3"
