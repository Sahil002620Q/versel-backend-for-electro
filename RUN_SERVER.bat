@echo off
echo Starting Information Marketplace...
echo.
echo Opening Site...
start http://localhost:8000
echo.
echo Server Running. Keep this window open.
python backend/simple_server.py
pause
