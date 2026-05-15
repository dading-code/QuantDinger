#!/bin/bash
# Check what's really happening with the backend

echo "=== 1. Gunicorn processes ==="
ps aux | grep gunicorn | grep -v grep

echo ""
echo "=== 2. Port 5000 status ==="
netstat -tlnp | grep 5000

echo ""
echo "=== 3. Test direct connection (3 second timeout) ==="
timeout 3 curl -v http://127.0.0.1:5000/api/health 2>&1

echo ""
echo "=== 4. Recent app logs ==="
tail -50 /var/log/quantdinger-backend.log | grep -v "Portfolio monitor" | grep -v "Reflection" | grep -v "Polymarket"
