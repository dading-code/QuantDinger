#!/bin/bash
# QuantDinger 99服务器后端修复脚本
# 解决502 Bad Gateway问题

set -e

echo "=========================================="
echo "QuantDinger 后端服务修复"
echo "=========================================="
echo ""

# 步骤1: 检查后端容器状态
echo "[1/5] 检查后端容器状态..."
CONTAINER_STATUS=$(podman ps -a --format '{{.Names}}: {{.Status}}' | grep backend || echo "NOT_FOUND")
echo "容器状态: $CONTAINER_STATUS"
echo ""

# 步骤2: 查看最近日志
echo "[2/5] 查看后端日志（最后50行）..."
podman logs backend --tail 50 2>&1 | tail -50
echo ""

# 步骤3: 停止旧容器
echo "[3/5] 停止旧容器..."
podman stop backend 2>/dev/null || true
podman rm backend 2>/dev/null || true
echo "✅ 旧容器已清理"
echo ""

# 步骤4: 拉取最新代码并重新构建
echo "[4/5] 更新代码并重新构建..."
cd /root/QuantDinger
git pull origin main || echo "⚠️ Git pull失败，使用现有代码"

# 重新构建并启动
docker-compose up -d --build backend
echo "✅ 后端容器已启动"
echo ""

# 步骤5: 等待服务启动并验证
echo "[5/5] 等待服务启动并验证..."
sleep 10

# 测试健康检查
HEALTH_CHECK=$(curl -s http://localhost:5000/api/health || echo "FAILED")
echo "健康检查响应: $HEALTH_CHECK"
echo ""

# 测试API Key路由
API_KEY_TEST=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/api/users/api-key/list)
echo "API Key接口状态码: $API_KEY_TEST"
echo ""

if [ "$API_KEY_TEST" = "401" ] || [ "$API_KEY_TEST" = "200" ]; then
    echo "✅ 后端服务正常！API Key接口可用"
else
    echo "❌ 后端服务异常，请查看日志"
    podman logs backend --tail 20
fi

echo ""
echo "=========================================="
echo "修复完成！"
echo "=========================================="
