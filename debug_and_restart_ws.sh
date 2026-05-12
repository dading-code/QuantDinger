#!/bin/bash
# Debug and restart WebSocket server

echo "=========================================="
echo "WebSocket Server Debug & Restart"
echo "=========================================="
echo ""

# Step 1: Check if port 8765 is actually listening
echo "[Step 1] Checking if port 8765 is listening..."
podman exec backend python3 << 'PYEOF'
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    result = s.connect_ex(('127.0.0.1', 8765))
    if result == 0:
        print("Port 8765: LISTENING")
    else:
        print(f"Port 8765: NOT LISTENING (error code: {result})")
except Exception as e:
    print(f"Error: {e}")
finally:
    s.close()
PYEOF

echo ""
echo "[Step 2] Checking WebSocket server script exists..."
podman exec backend ls -lh /app/start_websocket_server.py

echo ""
echo "[Step 3] Starting WebSocket server in background..."
# Kill any existing websocket server process
podman exec backend pkill -f start_websocket_server.py 2>/dev/null || true
sleep 1

# Start the WebSocket server in detached mode
podman exec -d backend python3 /app/start_websocket_server.py
echo "Started WebSocket server process"

echo ""
echo "[Step 4] Waiting for server to start (5 seconds)..."
sleep 5

echo ""
echo "[Step 5] Verifying server is running..."
podman exec backend python3 << 'PYEOF'
import socket
import time

# Try to connect to port 8765
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    result = s.connect_ex(('127.0.0.1', 8765))
    if result == 0:
        print("SUCCESS: Port 8765 is now LISTENING!")
        print("WebSocket server is running correctly.")
    else:
        print(f"FAIL: Port 8765 is still NOT listening (error: {result})")
except Exception as e:
    print(f"Error: {e}")
finally:
    s.close()
PYEOF

echo ""
echo "[Step 6] Checking recent logs..."
podman logs --tail 10 backend 2>&1 | grep -i "websocket\|8765" || echo "No WebSocket logs found"

echo ""
echo "=========================================="
echo "Done!"
echo "=========================================="
