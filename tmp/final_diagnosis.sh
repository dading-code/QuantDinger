#!/bin/bash
echo "=== 1. Backend容器IP地址 ==="
podman inspect backend --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}: {{$v.IPAddress}}{{end}}'

echo ""
echo "=== 2. 从Nginx容器访问backend:5000 ==="
podman exec quantdinger-frontend wget -qO- --timeout=3 http://backend:5000/api/health 2>&1 || echo "CONNECTION_FAILED"

echo ""
echo "=== 3. Backend容器内部监听状态 ==="
podman exec backend sh -c "netstat -tlnp 2>/dev/null | grep 5000 || ss -tlnp 2>/dev/null | grep 5000" 2>&1

echo ""
echo "=== 4. 后端日志（最后30行） ==="
podman logs --tail 30 backend 2>&1 | tail -30

echo ""
echo "=== 5. Gunicorn配置 ==="
podman exec backend cat /app/gunicorn_config.py 2>/dev/null | head -20
