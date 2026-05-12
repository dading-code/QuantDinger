#!/bin/bash
# Check if WebSocket server is running on port 8765

echo "Checking WebSocket server status..."
echo ""

podman exec backend python3 << 'PYEOF'
import socket

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    result = s.connect_ex(('localhost', 8765))
    if result == 0:
        print("✓ Port 8765 is LISTENING - WebSocket server is running")
    else:
        print(f"✗ Port 8765 is NOT listening (error code: {result})")
        print("\nWebSocket server is NOT running!")
        print("Start it with: python3 /app/start_websocket_server.py &")
    s.close()
except Exception as e:
    print(f"✗ Error checking port: {e}")
PYEOF
