#!/bin/bash

echo "=== Starting WebSocket Server ==="

# Copy WebSocket server script to container
podman cp /tmp/start_websocket_server.py backend:/app/start_websocket_server.py

# Start WebSocket server in background
podman exec -d backend python3 /app/start_websocket_server.py

# Wait a moment for startup
sleep 3

# Check if it's running
podman exec backend ps aux | grep websocket

echo ""
echo "=== Checking if port 8765 is listening ==="
podman exec backend ss -tlnp | grep 8765

echo ""
echo "=== WebSocket server started! ==="
