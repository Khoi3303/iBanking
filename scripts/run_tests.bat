@echo off
chcp 65001 > nul
echo ========================================================
echo  KHOI CHAY KIEM THU TU DONG CONCURRENCY - iBanking TDTU
echo ========================================================
echo.

python -m pip install -r scripts\requirements-test.txt > nul 2>&1
python scripts\test_concurrency.py

pause
