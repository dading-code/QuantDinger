#!/bin/bash
# Check backend logs for WebSocket authentication failures

echo "=========================================="
echo "Checking WebSocket Auth Logs"
echo "=========================================="
echo ""

# Check for any client rejection logs
echo "[1] Looking for client rejection logs..."
podman logs --tail 200 backend 2>&1 | grep -i -E 'reject|auth.*fail|invalid.*key|broker.*mismatch|4001|4002|websocket.*error' | tail -20

echo ""
echo "[2] Looking for WebSocket connection attempts..."
podman logs --tail 200 backend 2>&1 | grep -i -E 'websocket|client.*connect|register|8765' | tail -20

echo ""
echo "[3] Checking if WebSocket server is running on port 8765..."
podman exec backend python3 << 'PYEOF'
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    result = s.connect_ex(('127.0.0.1', 8765))
    if result == 0:
        print("✓ Port 8765 is LISTENING")
    else:
        print(f"✗ Port 8765 is NOT listening (code: {result})")
except Exception as e:
    print(f"✗ Error: {e}")
finally:
    s.close()
PYEOF

echo ""
echo "[4] Checking WebSocket Hub stats..."
curl -s http://localhost:8888/api/agent/v1/ws/stats 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "Cannot reach WebSocket stats API"

echo ""
echo "=========================================="
echo "If you see 'Client rejected' messages above,"
echo "that tells us WHY the connection is failing."
echo "=========================================="
