@echo off
chcp 65001 >nul
echo ========================================================
echo   DAY CODE MOI LEN GITHUB CHO CAC BAN TRONG NHOM
echo ========================================================
echo.

:: Dam bao go bo .env khoi Git tracking de khong bi lo thong tin mat khau/SMTP
git rm --cached .env >nul 2>&1
git rm --cached .env.local >nul 2>&1

echo [1/3] Trang thai cac file da thay doi:
git status -s
echo.

set /p msg="Nhap ghi chu commit (hoac nhan Enter de dung mac dinh): "
if "%msg%"=="" set msg=Cap nhat he thong iBanking

echo.
echo [2/3] Dang luu thay doi (git add + git commit)...
git add .
git commit -m "%msg%"

echo.
echo [3/3] Dang day len GitHub (git push origin)...
git push

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo   DA DAY LEN GITHUB THANH CONG!
    echo   Ban cua ban chi can mo terminal va go: git pull
    echo ========================================================
) else (
    echo.
    echo [!] Day len GitHub khong thanh cong. Vui long kiem tra ket noi mang hoac quyen truy cap repository.
)

echo.
pause
