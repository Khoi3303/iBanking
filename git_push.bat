@echo off
chcp 65001 >nul
echo ========================================================
echo   ĐẨY CODE MỚI LÊN GITHUB CHO CÁC BẠN TRONG NHÓM
echo ========================================================
echo.
echo [1/3] Trạng thái các file đã thay đổi:
git status -s
echo.

set /p msg="Nhập ghi chú commit (hoặc nhấn Enter để dùng mặc định): "
if "%msg%"=="" set msg=Cap nhat chuc nang nap tien, mac dinh 0d va cac script tien ich

echo.
echo [2/3] Đang lưu thay đổi (git add + git commit)...
git add .
git commit -m "%msg%"

echo.
echo [3/3] Đang đẩy lên GitHub (git push origin)...
git push

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo ✓ ĐÃ ĐẨY LÊN GITHUB THÀNH CÔNG!
    echo   Bạn của bạn chỉ cần mở terminal và gõ: git pull
    echo ========================================================
) else (
    echo.
    echo [!] Đẩy lên GitHub không thành công. Vui lòng kiểm tra kết nối mạng hoặc quyền truy cập repository.
)

echo.
pause
