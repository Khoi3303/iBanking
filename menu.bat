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
echo   [3] RESET TRẠNG THÁI DEMO (Đặt 524H0001 về UNPAID & nguyenvana 20tr)
echo   [4] Kiểm tra trạng thái các Container (docker compose ps)
echo   [5] Xem Log gửi Email (Notification Service - Gmail SMTP)
echo   [6] Xem Log điều phối giao dịch (Payment Service - Saga & OTP)
echo   [7] Chạy kiểm thử tự động Concurrency & Saga (Rubric chấm điểm)
echo   [8] Đẩy code mới lên GitHub (git add, commit & push)
echo   [9] Tắt toàn bộ hệ thống (docker compose down)
echo   [0] Thoát
echo.
echo ======================================================================
set /p opt="Vui lòng nhập lựa chọn của bạn [0-9]: "

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
echo Đang rebuild lại frontend, api-gateway và user-service...
docker compose up -d --build frontend api-gateway user-service
echo Hoàn tất! Nhấn Ctrl + F5 trên trình duyệt để kiểm tra.
pause
goto MENU

:RESET
echo.
echo Đang khôi phục hóa đơn 524H0001 về UNPAID và số dư nguyenvana = 20.000.000 VNĐ...
type database\reset_demo.sql | docker compose exec -T mysql mysql -u root -prootpassword
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
