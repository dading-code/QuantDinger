#!/bin/bash
cd /opt/quantdinger/QuantDinger/backend_api_python
source .venv/bin/activate

# Check if gevent is installed
python -c "import gevent; print('gevent version:', gevent.__version__)" 2>&1 || echo "gevent not installed"

# Check gunicorn status
echo ""
echo "=== Gunicorn processes ==="
ps aux | grep gunicorn | grep -v grep

echo ""
echo "=== Port 5000 ==="
netstat -tlnp | grep 5000 || echo "Port 5000 not listening"

echo ""
echo "=== Test API ==="
curl -s --max-time 5 http://127.0.0.1:5000/api/health || echo "API timeout"
