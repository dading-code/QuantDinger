#!/bin/bash
# Debug: Check iptables and restart gunicorn properly

echo "=== 1. Current iptables rules ==="
iptables -L -n -v | head -30

echo ""
echo "=== 2. Kill all gunicorn processes ==="
pkill -9 -f "gunicorn.*run:app"
sleep 2

echo "=== 3. Verify port 5000 is free ==="
netstat -tlnp | grep 5000 || echo "Port 5000 is free"

echo ""
echo "=== 4. Start gunicorn with debug logging ==="
cd /opt/quantdinger/QuantDinger/backend_api_python
source .venv/bin/activate

# Start with debug level logging
nohup gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 --log-level debug run:app > /var/log/quantdinger-backend.log 2>&1 &

echo "Waiting for gunicorn to start..."
sleep 8

echo ""
echo "=== 5. Check if listening ==="
netstat -tlnp | grep 5000

echo ""
echo "=== 6. Test API ==="
curl -v --max-time 5 http://127.0.0.1:5000/api/health 2>&1

echo ""
echo "=== 7. Recent gunicorn logs ==="
tail -30 /var/log/quantdinger-backend.log | grep -E "Starting|Listening|Worker|Error|Exception"
