#!/bin/bash
# 使用IP地址修复backend数据库连接

echo "=========================================="
echo "停止并删除backend容器"
echo "=========================================="
podman stop backend
podman rm backend

echo ""
echo "=========================================="
echo "重新创建backend容器（使用IP地址）"
echo "=========================================="

DB_IP=$(podman inspect quantdinger-db --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
echo "数据库IP地址: $DB_IP"

podman run -d \
  --name backend \
  --network quantdinger-network \
  -p 127.0.0.1:5000:5000 \
  --env-file /opt/quantdinger/QuantDinger/backend_api_python/.env \
  -e DATABASE_URL="postgresql://quantdinger:quantdinger123@${DB_IP}:5432/quantdinger" \
  -v backend_logs:/app/logs \
  -v backend_data:/app/data \
  -v /opt/quantdinger/QuantDinger/backend_api_python/.env:/app/.env \
  localhost/quantdinger-backend:latest

echo ""
echo "DATABASE_URL已设置为: postgresql://quantdinger:quantdinger123@${DB_IP}:5432/quantdinger"

echo ""
echo "=========================================="
echo "等待8秒后检查日志"
echo "=========================================="
sleep 8

echo ""
echo "最新的backend日志（查找数据库连接相关信息）："
podman logs --tail 40 backend | grep -i "database\|postgres\|connect\|pool\|ready\|error" || podman logs --tail 40 backend

echo ""
echo "=========================================="
echo "容器状态"
echo "=========================================="
podman ps | grep -E "backend|quantdinger-db"
