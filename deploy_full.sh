#!/bin/bash
# 全量部署脚本 - 更新后端并重启服务

echo "=========================================="
echo "QuantDinger 全量部署"
echo "=========================================="

cd /opt/quantdinger/QuantDinger

# 1. 拉取最新代码
echo ""
echo "[1/5] 拉取最新代码..."
git pull origin main

# 2. 复制后端代码到容器
echo ""
echo "[2/5] 复制后端代码到容器..."
podman cp backend_api_python backend:/app/backend_api_python

# 3. 重启backend容器
echo ""
echo "[3/5] 重启backend容器..."
podman restart backend

# 4. 等待服务启动
echo ""
echo "[4/5] 等待服务启动（10秒）..."
sleep 10

# 5. 验证服务状态
echo ""
echo "[5/5] 验证服务状态..."
podman logs --tail 30 backend | grep -E 'INFO|ERROR|WARNING' | tail -10

echo ""
echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo ""
echo "检查服务健康状态："
curl -s http://localhost:5000/api/health | python3 -m json.tool

echo ""
echo "测试API Key路由："
curl -s http://localhost:5000/api/user/api-keys | head -c 200
