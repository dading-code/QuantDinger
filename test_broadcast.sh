#!/bin/bash
# Test WebSocket broadcast by calling the API endpoint

echo "Testing WebSocket broadcast..."
echo ""

# Call the test broadcast endpoint
curl -X POST "http://39.105.150.99:8888/api/agent/v1/ws/broadcast/test" \
  -H "Content-Type: application/json" \
  -d '{}'

echo ""
echo ""
echo "Check your local client GUI - you should receive a test signal!"
