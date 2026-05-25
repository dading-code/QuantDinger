@echo off
cd /d D:\www\workai\qd-ai\QuantDinger\backend_api_python
set PYTHONIOENCODING=utf-8
start /B python run.py > logs\flask_out.log 2>&1
