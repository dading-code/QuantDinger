#!/bin/bash
# Apply WebSocket configuration to Nginx

echo "Applying WebSocket configuration..."

# Copy configuration to container
podman cp /tmp/nginx_websocket.conf quantdinger-frontend:/etc/nginx/conf.d/default.conf

# Test configuration
echo "Testing Nginx configuration..."
podman exec quantdinger-frontend nginx -t

if [ $? -eq 0 ]; then
    echo "✓ Configuration is valid"
    echo "Reloading Nginx..."
    podman exec quantdinger-frontend nginx -s reload
    echo "✓ Nginx reloaded successfully"
else
    echo "✗ Configuration test failed"
    exit 1
fi

# Verify WebSocket upstream
echo ""
echo "Verifying configuration..."
podman exec quantdinger-frontend cat /etc/nginx/conf.d/default.conf | grep -A 5 "location /ws"

echo ""
echo "Done!"
