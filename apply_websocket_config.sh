#!/bin/bash
# Fix WebSocket configuration in running container

echo "=========================================="
echo "Applying WebSocket Configuration"
echo "=========================================="

# Step 1: Copy the correct configuration
echo ""
echo "[Step 1] Uploading configuration..."
scp nginx_websocket.conf root@39.105.150.99:/tmp/nginx_websocket_fixed.conf

# Step 2: Apply to container
echo "[Step 2] Applying to container..."
ssh root@39.105.150.99 << 'ENDSSH'
    # Copy config into container
    podman cp /tmp/nginx_websocket_fixed.conf quantdinger-frontend:/etc/nginx/conf.d/default.conf
    
    # Test configuration
    echo "[Step 3] Testing Nginx configuration..."
    podman exec quantdinger-frontend nginx -t
    
    if [ $? -eq 0 ]; then
        echo "✓ Configuration test passed"
        
        # Reload Nginx (not restart container)
        echo "[Step 4] Reloading Nginx..."
        podman exec quantdinger-frontend nginx -s reload
        
        echo "✓ Nginx reloaded successfully"
    else
        echo "✗ Configuration test failed!"
        exit 1
    fi
ENDSSH

# Step 3: Verify
echo ""
echo "[Step 5] Verifying WebSocket route..."
ssh root@39.105.150.99 "podman exec quantdinger-frontend cat /etc/nginx/conf.d/default.conf | grep -A 8 'location /ws'"

echo ""
echo "=========================================="
echo "✅ Configuration applied!"
echo "=========================================="
echo ""
echo "Now run: python test_websocket_fix.py"
