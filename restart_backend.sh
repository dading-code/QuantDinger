#!/bin/bash
# Kill old gunicorn process and restart
kill -9 $(netstat -tlnp 2>/dev/null | grep :5000 | awk '{print $NF}' | cut -d'/' -f1 | head -1)
sleep 2

cd /opt/quantdinger/QuantDinger/backend_api_python
source .venv/bin/activate
nohup gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 run:app > /var/log/quantdinger-backend.log 2>&1 &

sleep 5
echo "Gunicorn restarted"
ps aux | grep gunicorn | grep -v grep | wc -l
