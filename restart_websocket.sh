#!/bin/bash

echo "=================================="
echo "Starting WebSocket Server"
echo "=================================="

# Step 1: Start WebSocket server
echo ""
echo "[Step 1] Starting WebSocket server in backend container..."

# Kill any existing websocket process first
podman exec backend pkill -f start_websocket_server.py 2>/dev/null || true
sleep 1

# Start WebSocket server in background
podman exec -d backend python3 /app/start_websocket_server.py

# Wait for startup
sleep 3

# Step 2: Verify it's running
echo ""
echo "[Step 2] Verifying WebSocket server..."

podman exec backend python3 -c "
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    result = s.connect_ex(('localhost', 8765))
    if result == 0:
        print('✓ Port 8765 is LISTENING - WebSocket server is running!')
    else:
        print(f'✗ Port 8765 is NOT listening (error: {result})')
    s.close()
except Exception as e:
    print(f'✗ Error: {e}')
"

# Step 3: Test from frontend container
echo ""
echo "[Step 3] Testing connection from frontend..."

# Check if backend:8765 is accessible
podman exec quantdinger-frontend sh -c "
if nc -z -w 2 backend 8765 2>/dev/null; then
    echo '✓ Frontend can reach backend:8765'
else
    echo '✗ Frontend CANNOT reach backend:8765'
fi
" 2>/dev/null || echo "nc command not available, trying alternative..."

# Step 4: Check logs
echo ""
echo "[Step 4] Checking WebSocket server logs..."
podman logs --tail 15 backend 2>&1 | grep -i websocket || echo "No recent websocket logs"

echo ""
echo "=================================="
echo "Done!"
echo "=================================="
echo ""
echo "If port 8765 is listening, restart your local client."
echo ""
