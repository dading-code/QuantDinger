#!/bin/bash
# 快速验证服务状态

echo "=========================================="
echo "服务状态验证"
echo "=========================================="

echo ""
echo "1. 检查容器状态："
podman ps | grep -E 'backend|frontend'

echo ""
echo "2. 检查后端健康状态："
curl -s http://localhost:5000/api/health || echo "后端未响应（可能通过Nginx代理）"

echo ""
echo "3. 检查前端健康状态："
curl -s http://localhost:80/ || echo "前端未响应"

echo ""
echo "4. 检查API Key路由："
curl -s http://localhost:5000/api/user/api-keys -H "Authorization: Bearer test" 2>&1 | head -c 300

echo ""
echo "5. 查看后端最新日志："
podman logs --tail 5 backend

echo ""
echo "=========================================="
echo "验证完成！"
echo "=========================================="
