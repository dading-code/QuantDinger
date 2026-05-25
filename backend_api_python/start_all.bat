@echo off
cd /d D:\www\workai\qd-ai\QuantDinger\backend_api_python
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
start "Flask" /B python run.py > logs\flask_out.log 2> logs\flask_err.log
timeout /t 8 /nobreak >nul
netstat -ano | findstr ":5000"
