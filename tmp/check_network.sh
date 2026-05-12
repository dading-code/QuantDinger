#!/bin/bash
echo "=== Backend Network ==="
podman inspect backend --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}: {{.IPAddress}}{{end}}'

echo ""
echo "=== Frontend Network ==="
podman inspect quantdinger-frontend --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}: {{.IPAddress}}{{end}}'

echo ""
echo "=== Nginx Config ==="
# Check if nginx config exists in various locations
for conf in /etc/nginx/conf.d/*.conf /etc/nginx/nginx.conf; do
    if [ -f "$conf" ]; then
        echo "--- $conf ---"
        grep -A 5 "proxy_pass.*backend" "$conf" 2>/dev/null || grep -A 5 "proxy_pass.*5000" "$conf" 2>/dev/null
    fi
done

echo ""
echo "=== Test Backend from Host ==="
# Try to access backend via container name
BACKEND_IP=$(podman inspect backend --format '{{range $k, $v := .NetworkSettings.Networks}}{{$v.IPAddress}}{{end}}' | head -1)
echo "Backend IP: $BACKEND_IP"
if [ -n "$BACKEND_IP" ]; then
    curl -s -o /dev/null -w "HTTP Status from backend IP: %{http_code}\n" "http://$BACKEND_IP:5000/api/health"
fi

echo ""
echo "=== Test Backend via podman network ==="
podman run --rm --network quantdinger-network alpine/curl curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" "http://backend:5000/api/health"
