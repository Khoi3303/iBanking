@echo off
chcp 65001 >nul
echo ========================================================
echo   KHOI DONG HE THONG iBanking MICROSERVICES (TDTU SOA)
echo ========================================================

echo [1/3] Dang don dep cac container va volume cu...
docker compose down -v

echo.
echo [2/3] Dang build lai Docker image va khoi chay...
docker compose up --build -d

echo.
echo [3/3] Dang doi MySQL khoi tao co so du lieu va nap du lieu mau...
timeout /t 15 /nobreak >nul

echo.
echo ========================================================
echo   TRANG THAI CAC DICH VU:
echo ========================================================
docker compose ps

echo.
echo ========================================================
echo   HE THONG DA SAN SANG!
echo   - Giao dien: http://localhost:3000
echo   - Tai khoan 1: nguyenvana     (nguyenvana@ibanking.tdtu.edu.vn) | MK: 123456 | 20tr VND
echo   - Tai khoan 2: lekhoi3303     (lekhoi3303@ibanking.tdtu.edu.vn) | MK: 123456 | 20tr VND
echo   - Tai khoan 3: tienmobile2006 (tienmobile@ibanking.tdtu.edu.vn) | MK: 123456 | 20tr VND
echo   - Tai khoan 4: mensieu123     (mensieu@ibanking.tdtu.edu.vn)    | MK: 123456 | 20tr VND
echo   - Luu y: De nhan OTP qua hop thu that, cap nhat SMTP_USER va SMTP_PASSWORD trong file .env
echo ========================================================
pause
