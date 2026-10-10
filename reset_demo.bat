@echo off
chcp 65001 >nul
echo ========================================================
echo   KHÔI PHỤC TRẠNG THÁI DEMO (RESET THANH TOÁN 524H0001)
echo ========================================================
echo.
echo Đang đặt lại hóa đơn 524H0001 thành UNPAID...
echo Đang đặt lại số dư nguyenvana = 20.000.000 VNĐ...
echo.

type database\reset_demo.sql | docker compose exec -T mysql mysql -u root -prootpassword

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo ✓ ĐÃ KHÔI PHỤC THÀNH CÔNG!
    echo   - Sinh viên 524H0001: Trạng thái UNPAID (Còn nợ 15.000.000 VNĐ)
    echo   - Tài khoản nguyenvana: Số dư 20.000.000 VNĐ
    echo   - Bạn có thể tải lại trang (F5) và thanh toán lại ngay bây giờ.
    echo ========================================================
) else (
    echo.
    echo [!] Có lỗi xảy ra khi kết nối vào MySQL container.
    echo     Hãy đảm bảo Docker Desktop đang chạy và container mysql đang bật.
)

echo.
pause
