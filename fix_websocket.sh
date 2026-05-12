#!/bin/bash

echo "=================================="
echo "Fixing WebSocket Connection"
echo "=================================="

# Step 1: Start WebSocket server in backend container
echo ""
echo "[Step 1] Starting WebSocket server..."
podman cp /tmp/start_websocket_server.py backend:/app/start_websocket_server.py

# Start as background process inside container
podman exec -d backend python3 /app/start_websocket_server.py

# Check if running by testing the port
sleep 3
if podman exec backend python3 -c "import socket; s = socket.socket(); s.settimeout(2); s.connect(('localhost', 8765)); s.close(); print('OK')" 2>/dev/null; then
    echo "✓ WebSocket server started"
else
    echo "✗ WebSocket server failed to start"
    podman logs --tail 20 backend 2>&1 | tail -10
    exit 1
fi

# Step 2: Update Nginx configuration to add WebSocket proxy
echo ""
echo "[Step 2] Updating Nginx configuration..."

# Create new nginx config with WebSocket proxy
cat > /tmp/nginx.conf << 'NGINX_EOF'
upstream backend_api {
    server backend:5000;
}

upstream websocket_server {
    server backend:8765;
}

server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1000;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript image/svg+xml;

    # Static asset caching (hashed filenames = immutable)
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot|map)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # API proxy to backend
    location /api/ {
        proxy_pass http://backend_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 600s;
        proxy_connect_timeout 75s;
        proxy_send_timeout 600s;
        client_max_body_size 10m;
    }

    # WebSocket proxy
    location /ws {
        proxy_pass http://websocket_server;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # SPA routing support (all routes fall back to index.html)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Health check endpoint
    location /health {
        return 200 'OK';
        add_header Content-Type text/plain;
        access_log off;
    }
}
NGINX_EOF

# Copy to container
podman cp /tmp/nginx.conf quantdinger-frontend:/etc/nginx/conf.d/default.conf

# Reload Nginx
podman exec quantdinger-frontend nginx -s reload

echo "✓ Nginx configuration updated"

# Step 3: Verify everything
echo ""
echo "[Step 3] Verification..."
sleep 2

echo ""
echo "Checking WebSocket server:"
podman exec backend python3 -c "import socket; s = socket.socket(); s.settimeout(2); s.connect(('localhost', 8765)); s.close(); print('Port 8765 is listening')" 2>/dev/null || echo "Port 8765 is not responding"

echo ""
echo "Checking Nginx config:"
podman exec quantdinger-frontend cat /etc/nginx/conf.d/default.conf | grep -A 5 "location /ws"

echo ""
echo "=================================="
echo "✓ WebSocket fix completed!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Restart local client"
echo "2. Check if WebSocket connection shows '已连接'"
echo ""
