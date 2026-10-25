@echo off
chcp 65001 >nul
echo ========================================================
echo   KHOI PHUC TRANG THAI DEMO (RESET THANH TOAN 524H0001)
echo ========================================================
echo.
echo Dang dat lai hoa don 524H0001 thanh UNPAID...
echo Dang dat lai so du nguyenvana = 20.000.000 VND...
echo.

if exist fix.sql del /f /q fix.sql >nul 2>&1
if exist database\fix_utf8.sql del /f /q database\fix_utf8.sql >nul 2>&1
if exist database\add_test_accounts.sql del /f /q database\add_test_accounts.sql >nul 2>&1
if exist nap_tai_khoan_ngay.bat del /f /q nap_tai_khoan_ngay.bat >nul 2>&1

docker compose exec -T mysql mysql --default-character-set=utf8mb4 -u root -prootpassword < database\reset_demo.sql

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo   DA KHOI PHUC THANH CONG!
    echo   - Trang thai hoa don: Da chuyen ve UNPAID
    echo   - So du tai khoan: 20.000.000 VND
    echo   - Ban co the tai lai trang (F5) va thuc hien thanh toan lai.
    echo ========================================================
) else (
    echo.
    echo [LOI] Khong the ket noi vao MySQL container.
    echo       Hay dam bao Docker Desktop dang chay va container mysql dang bat.
)

echo.
pause
