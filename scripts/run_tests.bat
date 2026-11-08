@echo off
set "PATH=%SystemRoot%\System32;%SystemRoot%;%PATH%"
chcp 65001 > nul 2>&1
cd /d "%~dp0.."

echo ========================================================
echo  KHOI CHAY KIEM THU TU DONG CONCURRENCY - iBanking TDTU
echo ========================================================
echo.

python -m pip install -r scripts\requirements-test.txt > nul 2>&1
python scripts\test_concurrency.py

echo.
pause
