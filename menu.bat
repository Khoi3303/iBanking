@echo off
chcp 65001 >nul
:MENU
cls
echo ======================================================================
echo          iBanking TDTU - BANG DIEU KHIEN VA LENH NHANH (SOA)
echo ======================================================================
echo.
echo   [1] Khoi dong toan bo he thong (docker compose up -d)
echo   [2] Rebuild nhanh cac service da sua (Frontend, Gateway, User Service)
echo   [3] Reset trang thai du lieu demo (Dat hoa don ve UNPAID va so du 20tr)
echo   [4] Kiem tra trang thai cac Container (docker compose ps)
echo   [5] Xem Log gui Email (Notification Service - SMTP)
echo   [6] Xem Log dieu phoi giao dich (Payment Service - Saga va OTP)
echo   [7] Chay kiem thu tu dong Concurrency va Saga
echo   [8] Day code moi len GitHub (git_push.bat)
echo   [9] Tat toan bo he thong (docker compose down)
echo   [0] Thoat
echo.
echo ======================================================================
set /p opt="Vui long nhap lua chon cua ban: "

if "%opt%"=="1" goto START
if "%opt%"=="2" goto REBUILD
if "%opt%"=="3" goto RESET
if "%opt%"=="4" goto STATUS
if "%opt%"=="5" goto LOG_MAIL
if "%opt%"=="6" goto LOG_PAY
if "%opt%"=="7" goto TEST
if "%opt%"=="8" goto GIT_PUSH
if "%opt%"=="9" goto STOP
if "%opt%"=="0" exit
goto MENU

:START
echo.
echo Dang khoi dong he thong...
docker compose up -d
echo Hoan tat!
pause
goto MENU

:REBUILD
echo.
echo Dang rebuild va cap nhat cac dich vu...
if exist fix.sql del /f /q fix.sql >nul 2>&1
if exist database\fix_utf8.sql del /f /q database\fix_utf8.sql >nul 2>&1
if exist database\add_test_accounts.sql del /f /q database\add_test_accounts.sql >nul 2>&1
if exist nap_tai_khoan_ngay.bat del /f /q nap_tai_khoan_ngay.bat >nul 2>&1
docker compose exec -T mysql mysql --default-character-set=utf8mb4 -u root -prootpassword < database\reset_demo.sql >nul 2>&1
docker compose up -d --build --remove-orphans frontend api-gateway user-service tuition-service payment-service notification-service
echo Hoan tat! Nhan Ctrl + F5 tren trinh duyet de kiem tra.
pause
goto MENU

:RESET
echo.
echo Dang khoi phuc hoa don hoc phi ve UNPAID va so du ve 20.000.000 VND...
docker compose exec -T mysql mysql --default-character-set=utf8mb4 -u root -prootpassword < database\reset_demo.sql
echo Hoan tat! Ban co the thanh toan lai ngay.
pause
goto MENU

:STATUS
echo.
docker compose ps
pause
goto MENU

:LOG_MAIL
echo.
echo Dang xem log Notification Service (Nhan Ctrl + C de quay lai menu)...
docker compose logs -f notification-service
goto MENU

:LOG_PAY
echo.
echo Dang xem log Payment Service (Nhan Ctrl + C de quay lai menu)...
docker compose logs -f payment-service
goto MENU

:TEST
echo.
echo Dang chay kich ban kiem thu tu dong Concurrency va Saga...
python scripts\test_concurrency.py
pause
goto MENU

:GIT_PUSH
echo.
call git_push.bat
goto MENU

:STOP
echo.
echo Dang tat toan bo he thong...
docker compose down
echo Da tat hoan tat.
pause
goto MENU
