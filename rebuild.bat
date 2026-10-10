@echo off
chcp 65001 >nul
echo ========================================================
echo   CẬP NHẬT & REBUILD NHANH CÁC DỊCH VỤ ĐÃ THAY ĐỔI
echo ========================================================
echo Đang build lại user-service, api-gateway và frontend...
docker compose up -d --build user-service api-gateway frontend
echo.
echo Hoàn tất! Vui lòng tải lại trang http://localhost:3000 (Ctrl + F5).
pause
