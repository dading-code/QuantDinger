#!/bin/bash

echo "=================================="
echo "Checking WebSocket Server Status"
echo "=================================="

# Test 1: Check if WebSocket server is running in backend container
echo ""
echo "[Test 1] Checking port 8765 in backend container..."
podman exec backend python3 << 'PYEOF'
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    result = s.connect_ex(('localhost', 8765))
    if result == 0:
        print("✓ Port 8765 is LISTENING")
    else:
        print(f"✗ Port 8765 is NOT listening (error code: {result})")
    s.close()
except Exception as e:
    print(f"✗ Error checking port: {e}")
PYEOF

# Test 2: Try WebSocket connection from frontend container
echo ""
echo "[Test 2] Testing WebSocket connection from frontend container..."
podman exec quantdinger-frontend python3 << 'PYEOF'
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    result = s.connect_ex(('backend', 8765))
    if result == 0:
        print("✓ Can connect to backend:8765 from frontend container")
    else:
        print(f"✗ Cannot connect to backend:8765 (error code: {result})")
    s.close()
except Exception as e:
    print(f"✗ Error: {e}")
PYEOF

# Test 3: Check running processes in backend
echo ""
echo "[Test 3] Checking for websocket processes..."
podman exec backend sh -c "ps aux 2>/dev/null || ps -ef 2>/dev/null || echo 'ps command not available'" | grep -i websocket || echo "No websocket process found"

# Test 4: Check Nginx upstream configuration
echo ""
echo "[Test 4] Checking Nginx upstream config..."
podman exec quantdinger-frontend cat /etc/nginx/conf.d/default.conf | grep -A 2 "upstream websocket"

echo ""
echo "=================================="
echo "Summary"
echo "=================================="
echo ""
echo "If port 8765 is not listening, the WebSocket server is not running."
echo "You need to start it with:"
echo "  podman exec -d backend python3 /app/start_websocket_server.py"
echo ""
