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
echo   - Giao diện: http://localhost:3000
echo   - Tài khoản 1: nguyenvana     (khoi18042006@gmail.com)   | MK: 123456 | 20tr VNĐ
echo   - Tài khoản 2: lekhoi3303     (lekhoi3303@gmail.com)     | MK: 123456 | 20tr VNĐ
echo   - Tài khoản 3: tienmobile2006 (tienmobile2006@gmail.com) | MK: 123456 | 20tr VNĐ
echo   - Tài khoản 4: mensieu123     (Mensieu123@gmail.com)     | MK: 123456 | 20tr VNĐ
echo   - Mã OTP được gửi trực tiếp đến Gmail thật (Kiểm tra Inbox / Spam)
echo ========================================================
pause
