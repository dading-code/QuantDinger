#!/bin/bash
# Check WebSocket hub stats and client connections

echo "Checking WebSocket Hub Status..."
echo ""

# Get hub statistics
curl -s "http://39.105.150.99:8888/api/agent/v1/ws/stats" | python3 -m json.tool

echo ""
echo "If active_connections is 0, the client is not properly registered."
echo ""
echo "Check backend logs for WebSocket registration:"
ssh root@39.105.150.99 "podman logs --tail 50 backend 2>&1 | grep -i 'websocket\|client.*register\|auth.*success\|api.*key'"
