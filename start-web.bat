@echo off
chcp 65001 >nul
echo ========================================
echo    KrillinAI - Web Server
echo ========================================
echo.
echo Dang khoi dong server...
echo Mo trinh duyet va truy cap: http://127.0.0.1:8888
echo.
start "" http://127.0.0.1:8888
.\build\krillinai-server.exe
echo.
echo Server da dung.
pause
