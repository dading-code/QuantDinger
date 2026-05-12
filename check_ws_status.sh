#!/bin/bash
# Check if WebSocket server is running

echo "Checking WebSocket server (port 8765)..."

# Try to connect to port 8765
podman exec backend python3 << 'EOF'
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
result = s.connect_ex(('127.0.0.1', 8765))
if result == 0:
    print("✓ Port 8765 is LISTENING")
else:
    print(f"✗ Port 8765 is NOT listening (code: {result})")
s.close()
EOF

echo ""
echo "Checking for websocket processes..."
podman exec backend sh -c "ps aux 2>/dev/null | grep websocket || echo 'ps command not available'"
