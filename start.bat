@echo off
chcp 65001 >nul
echo ========================================================
echo   KHỞI ĐỘNG HỆ THỐNG iBanking MICROSERVICES (TDTU SOA)
echo ========================================================

echo [1/3] Đang dọn dẹp các container và volume cũ...
docker compose down -v

echo.
echo [2/3] Đang build lại Docker image và khởi chạy...
docker compose up --build -d

echo.
echo [3/3] Đang đợi MySQL khởi tạo cơ sở dữ liệu và nạp dữ liệu mẫu...
timeout /t 15 /nobreak >nul

echo.
echo ========================================================
echo   TRẠNG THÁI CÁC DỊCH VỤ:
echo ========================================================
docker compose ps

echo.
echo ========================================================
echo   HỆ THỐNG ĐÃ SẴN SÀNG!
echo   - Giao diện người dùng: http://localhost:3000
echo   - Tài khoản mẫu: nguyenvana
echo   - Mật khẩu: 123456
echo   - Hòm thư xem OTP (Mailpit): http://localhost:8025
echo ========================================================
pause
