@echo off
chcp 65001 >nul
echo ========================================================
echo   GO BO THEO DOI .ENV VA CAC FILE NHAY CAM KHOI GIT
echo ========================================================
echo.
echo Dang go bo file .env khoi Git tracking (khong lam mat file goc tren may)...
git rm --cached .env >nul 2>&1
git rm --cached .env.local >nul 2>&1
git rm --cached -r --ignore-unmatch .vscode .idea *.log logs __pycache__ >nul 2>&1

echo.
echo Kiem tra trang thai Git:
git status -s

echo.
echo ========================================================
echo Da hoan tat!
echo Bay gio file .env da duoc giu lai tren may nhung se KHONG
echo bi day len GitHub nua.
echo ========================================================
echo.
pause
