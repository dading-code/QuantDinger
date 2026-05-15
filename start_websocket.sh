#!/bin/bash
cd /opt/quantdinger/QuantDinger
source backend_api_python/.venv/bin/activate

# Check websockets
python -c "import websockets; print('websockets version:', websockets.__version__)" 2>&1 || echo "websockets not installed"

# Start WebSocket server in background
echo ""
echo "=== Starting WebSocket server ==="
nohup python start_websocket_server.py > /var/log/quantdinger-websocket.log 2>&1 &

sleep 3

# Check if running
ps aux | grep websocket | grep -v grep
netstat -tlnp | grep 8765 || echo "Port 8765 not listening"

echo ""
echo "=== WebSocket log (last 20 lines) ==="
tail -20 /var/log/quantdinger-websocket.log
