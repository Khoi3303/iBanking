@echo off
chcp 65001 >nul
echo ========================================================
echo   KHÔI PHỤC TRẠNG THÁI DEMO (RESET THANH TOÁN 524H0001)
echo ========================================================
echo.
echo Đang đặt lại hóa đơn 524H0001 thành UNPAID...
echo Đang đặt lại số dư nguyenvana = 20.000.000 VNĐ...
echo.

if exist fix.sql del /f /q fix.sql >nul 2>&1
if exist database\fix_utf8.sql del /f /q database\fix_utf8.sql >nul 2>&1
if exist database\add_test_accounts.sql del /f /q database\add_test_accounts.sql >nul 2>&1
if exist nap_tai_khoan_ngay.bat del /f /q nap_tai_khoan_ngay.bat >nul 2>&1

docker compose exec -T mysql mysql --default-character-set=utf8mb4 -u root -prootpassword < database\reset_demo.sql

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo   ĐÃ KHÔI PHỤC THÀNH CÔNG!
    echo   - Trạng thái hóa đơn: Đã chuyển về UNPAID
    echo   - Số dư tài khoản: 20.000.000 VNĐ
    echo   - Bạn có thể tải lại trang (F5) và thực hiện thanh toán lại.
    echo ========================================================
) else (
    echo.
    echo [LỖI] Không thể kết nối vào MySQL container.
    echo       Hãy đảm bảo Docker Desktop đang chạy và container mysql đang bật.
)

echo.
pause
