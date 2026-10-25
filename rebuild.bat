@echo off
set "PATH=%SystemRoot%\System32;%SystemRoot%;%PATH%"
chcp 65001 >nul
echo ========================================================
echo   CAP NHAT VA REBUILD NHANH CAC DICH VU DA THAY DOI
echo ========================================================
echo.
echo [1/2] Dang don dep file tam va cap nhat cac dich vu...
if exist fix.sql del /f /q fix.sql >nul 2>&1
if exist database\fix_utf8.sql del /f /q database\fix_utf8.sql >nul 2>&1
if exist database\add_test_accounts.sql del /f /q database\add_test_accounts.sql >nul 2>&1
if exist nap_tai_khoan_ngay.bat del /f /q nap_tai_khoan_ngay.bat >nul 2>&1
docker compose up -d --build --remove-orphans user-service tuition-service payment-service notification-service api-gateway frontend

echo.
set DB_ROOT_PASS=rootpassword
if exist .env (
    for /f "tokens=2 delims==" %%A in ('findstr /b "MYSQL_ROOT_PASSWORD=" .env') do set "DB_ROOT_PASS=%%A"
)
docker compose exec -T -e MYSQL_PWD=%DB_ROOT_PASS% mysql mysql --default-character-set=utf8mb4 -u root < database\reset_demo.sql

echo.
echo ========================================================
echo   HOAN TAT CAP NHAT!
echo   - Cac tai khoan san sang: nguyenvana, lekhoi3303, tienmobile2006, mensieu123
echo   - Mat khau: 123456 (So du: 20.000.000 VND)
echo   - Danh sach hon 15 MSSV no hoc phi san sang kiem thu
echo ========================================================
echo Vui long mo lai trinh duyet va nhan Ctrl + F5 de kiem tra!
echo.
pause
