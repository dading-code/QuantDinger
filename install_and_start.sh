#!/bin/bash
cd /opt/quantdinger/QuantDinger/backend_api_python
source .venv/bin/activate

echo "=== Installing gevent ==="
pip install gevent

echo ""
echo "=== Starting Gunicorn with gevent workers ==="
nohup gunicorn --bind 0.0.0.0:5000 --workers 8 --worker-class gevent --timeout 120 run:app > /var/log/quantdinger-backend.log 2>&1 &

echo "Waiting for startup..."
sleep 8

echo ""
echo "=== Check processes ==="
ps aux | grep gunicorn | grep -v grep | wc -l

echo ""
echo "=== Check port ==="
netstat -tlnp | grep 5000 || echo "Port not listening"

echo ""
echo "=== Test API ==="
curl -s --max-time 5 http://127.0.0.1:5000/api/health || echo "API timeout"
