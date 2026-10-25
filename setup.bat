@echo off
chcp 65001 >nul
echo ======================================================================
echo          iBanking TDTU - Quick Setup Script (Windows)
echo ======================================================================
echo.

where powershell >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PowerShell is required to run setup script.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ======================================================================
    echo [ERROR] Qua trinh khoi tao hoac xac thuc cau hinh that bai (Exit code: %ERRORLEVEL%).
    echo Vui long kiem tra thong bao loi o tren va sua file .env truoc khi khoi chay.
    echo ======================================================================
    pause
    exit /b %ERRORLEVEL%
)
set /p START_NOW="Ban co muon khoi chay Docker Compose ngay bay gio khong? (Y/N, default Y): "
if /i "%START_NOW%"=="N" (
    echo Ban co the chay he thong bat ky luc nao bang lenh: docker compose up -d --build
    pause
    exit /b 0
)

echo.
echo Dang khoi dong cac dich vu iBanking qua Docker Compose...
docker compose up -d --build
echo.
echo ======================================================================
echo He thong dang duoc khoi chay tai http://localhost:3000
echo ======================================================================
pause
