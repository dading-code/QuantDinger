#!/bin/bash
# Check WebSocket server status

echo "=========================================="
echo "Checking WebSocket Server"
echo "=========================================="
echo ""

# Check if port 8765 is listening
echo "[1] Checking port 8765..."
podman exec backend python3 << 'PYEOF'
import socket

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    result = s.connect_ex(('127.0.0.1', 8765))
    if result == 0:
        print("✓ Port 8765 is LISTENING")
    else:
        print(f"✗ Port 8765 is NOT listening (code: {result})")
    s.close()
except Exception as e:
    print(f"✗ Error: {e}")
PYEOF

echo ""
echo "[2] Checking WebSocket server logs..."
podman logs backend 2>&1 | grep -i "websocket.*server\|start.*websocket\|8765" | tail -5

echo ""
echo "[3] Checking for recent connection attempts..."
podman logs backend 2>&1 | grep -i "client\|auth\|reject\|400\|4001\|invalid" | tail -10

echo ""
echo "=========================================="
