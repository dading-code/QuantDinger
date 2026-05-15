#!/bin/bash
# 修复backend数据库连接问题

echo "=========================================="
echo "停止并删除backend容器"
echo "=========================================="
podman stop backend
podman rm backend

echo ""
echo "=========================================="
echo "重新创建backend容器（使用正确的DATABASE_URL）"
echo "=========================================="

# 从.env文件加载环境变量
source /opt/quantdinger/QuantDinger/backend_api_python/.env

podman run -d \
  --name backend \
  --network quantdinger-network \
  -p 127.0.0.1:5000:5000 \
  --env-file /opt/quantdinger/QuantDinger/backend_api_python/.env \
  -e DATABASE_URL="postgresql://quantdinger:quantdinger123@quantdinger-db:5432/quantdinger" \
  -v backend_logs:/app/logs \
  -v backend_data:/app/data \
  -v /opt/quantdinger/QuantDinger/backend_api_python/.env:/app/.env \
  localhost/quantdinger-backend:latest

echo ""
echo "=========================================="
echo "等待5秒后检查日志"
echo "=========================================="
sleep 5

echo ""
echo "最新的backend日志："
podman logs --tail 30 backend

echo ""
echo "=========================================="
echo "容器状态"
echo "=========================================="
podman ps | grep -E "backend|quantdinger-db"
