@echo off
chcp 65001 >nul
:MENU
cls
echo ======================================================================
echo          iBanking TDTU - BẢNG ĐIỀU KHIỂN & LỆNH NHANH (SOA)
echo ======================================================================
echo.
echo   [1] Khởi động toàn bộ hệ thống (docker compose up -d)
echo   [2] Rebuild nhanh các service đã sửa (Frontend, Gateway, User Service)
echo   [3] Reset trạng thái dữ liệu demo (Đặt hóa đơn về UNPAID & số dư 20tr)
echo   [4] Kiểm tra trạng thái các Container (docker compose ps)
echo   [5] Xem Log gửi Email (Notification Service - SMTP)
echo   [6] Xem Log điều phối giao dịch (Payment Service - Saga & OTP)
echo   [7] Chạy kiểm thử tự động Concurrency & Saga
echo   [8] Đẩy code mới lên GitHub (git_push.bat)
echo   [9] Tắt toàn bộ hệ thống (docker compose down)
echo   [0] Thoát
echo.
echo ======================================================================
set /p opt="Vui lòng nhập lựa chọn của bạn: "

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
echo Đang khởi động hệ thống...
docker compose up -d
echo Hoàn tất!
pause
goto MENU

:REBUILD
echo.
echo Đang rebuild và cập nhật các dịch vụ...
if exist fix.sql del /f /q fix.sql >nul 2>&1
if exist database\fix_utf8.sql del /f /q database\fix_utf8.sql >nul 2>&1
if exist database\add_test_accounts.sql del /f /q database\add_test_accounts.sql >nul 2>&1
if exist nap_tai_khoan_ngay.bat del /f /q nap_tai_khoan_ngay.bat >nul 2>&1
docker compose exec -T mysql mysql --default-character-set=utf8mb4 -u root -prootpassword < database\reset_demo.sql >nul 2>&1
docker compose up -d --build --remove-orphans frontend api-gateway user-service tuition-service payment-service notification-service
echo Hoàn tất! Nhấn Ctrl + F5 trên trình duyệt để kiểm tra.
pause
goto MENU

:RESET
echo.
echo Đang khôi phục hóa đơn học phí về UNPAID và số dư về 20.000.000 VNĐ...
docker compose exec -T mysql mysql --default-character-set=utf8mb4 -u root -prootpassword < database\reset_demo.sql
echo Hoàn tất! Bạn có thể thanh toán lại ngay.
pause
goto MENU

:STATUS
echo.
docker compose ps
pause
goto MENU

:LOG_MAIL
echo.
echo Đang xem log Notification Service (Nhấn Ctrl + C để quay lại menu)...
docker compose logs -f notification-service
goto MENU

:LOG_PAY
echo.
echo Đang xem log Payment Service (Nhấn Ctrl + C để quay lại menu)...
docker compose logs -f payment-service
goto MENU

:TEST
echo.
echo Đang chạy kịch bản kiểm thử tự động Concurrency & Saga...
python scripts\test_concurrency.py
pause
goto MENU

:GIT_PUSH
echo.
call git_push.bat
goto MENU

:STOP
echo.
echo Đang tắt toàn bộ hệ thống...
docker compose down
echo Đã tắt hoàn tất.
pause
goto MENU
