@echo off
chcp 65001 >nul
echo ========================================================
echo   CẬP NHẬT & REBUILD NHANH CÁC DỊCH VỤ ĐÃ THAY ĐỔI
echo ========================================================
echo.
echo [1/2] Đang dọn dẹp file tạm và cập nhật các dịch vụ...
if exist fix.sql del /f /q fix.sql >nul 2>&1
if exist database\fix_utf8.sql del /f /q database\fix_utf8.sql >nul 2>&1
if exist database\add_test_accounts.sql del /f /q database\add_test_accounts.sql >nul 2>&1
if exist nap_tai_khoan_ngay.bat del /f /q nap_tai_khoan_ngay.bat >nul 2>&1
docker compose up -d --build --remove-orphans user-service tuition-service payment-service notification-service api-gateway frontend

echo.
echo [2/2] Đang cập nhật cơ sở dữ liệu mẫu...
docker compose exec -T mysql mysql --default-character-set=utf8mb4 -u root -prootpassword < database\reset_demo.sql

echo.
echo ========================================================
echo   HOÀN TẤT CẬP NHẬT!
echo   - Các tài khoản sẵn sàng: nguyenvana, lekhoi3303, tienmobile2006, mensieu123
echo   - Mật khẩu: 123456 (Số dư: 20.000.000 VNĐ)
echo   - Danh sách hơn 15 MSSV nợ học phí sẵn sàng kiểm thử
echo ========================================================
echo Vui lòng mở lại trình duyệt và nhấn Ctrl + F5 để kiểm tra!
echo.
pause
