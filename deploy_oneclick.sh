#!/bin/bash
# QuantDinger 一键部署脚本 v2.0
# 用途: 自动同步代码、更新容器、验证服务
# 使用: bash deploy_oneclick.sh

set -e  # 遇到错误立即退出

echo "=========================================="
echo "QuantDinger 一键部署 v2.0"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
SERVER_IP="39.105.150.99"
SERVER_USER="root"
PROJECT_DIR="/opt/quantdinger/QuantDinger"

# 检查SSH连接
echo -e "${YELLOW}[0/6] 检查SSH连接...${NC}"
if ! ssh -o ConnectTimeout=5 ${SERVER_USER}@${SERVER_IP} "echo OK" > /dev/null 2>&1; then
    echo -e "${RED}❌ 无法连接到服务器 ${SERVER_IP}${NC}"
    exit 1
fi
echo -e "${GREEN}✅ SSH连接正常${NC}"
echo ""

# 步骤1: 上传所有后端代码
echo -e "${YELLOW}[1/6] 上传后端代码到服务器...${NC}"
rsync -avz --delete \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='node_modules' \
    --exclude='venv' \
    backend_api_python/ ${SERVER_USER}@${SERVER_IP}:${PROJECT_DIR}/backend_api_python/

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 代码上传成功${NC}"
else
    echo -e "${RED}❌ 代码上传失败${NC}"
    exit 1
fi
echo ""

# 步骤2: 复制代码到backend容器
echo -e "${YELLOW}[2/6] 复制代码到backend容器...${NC}"
ssh ${SERVER_USER}@${SERVER_IP} << 'EOF'
cd /opt/quantdinger/QuantDinger
podman cp backend_api_python backend:/app/backend_api_python
echo "✅ 代码已复制到容器"
EOF
echo ""

# 步骤3: 重启backend容器
echo -e "${YELLOW}[3/6] 重启backend容器...${NC}"
ssh ${SERVER_USER}@${SERVER_IP} "podman restart backend"
echo -e "${GREEN}✅ Backend容器已重启${NC}"
echo ""

# 步骤4: 等待服务启动
echo -e "${YELLOW}[4/6] 等待服务启动（10秒）...${NC}"
sleep 10
echo -e "${GREEN}✅ 等待完成${NC}"
echo ""

# 步骤5: 重启frontend刷新DNS
echo -e "${YELLOW}[5/6] 重启frontend容器（刷新DNS缓存）...${NC}"
ssh ${SERVER_USER}@${SERVER_IP} "podman restart quantdinger-frontend"
echo -e "${GREEN}✅ Frontend容器已重启${NC}"
echo ""

# 步骤6: 验证服务
echo -e "${YELLOW}[6/6] 验证服务状态...${NC}"
sleep 5

# 健康检查
HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://${SERVER_IP}:8888/api/health)
if [ "$HEALTH_CHECK" = "200" ]; then
    echo -e "${GREEN}✅ 健康检查通过 (HTTP 200)${NC}"
else
    echo -e "${RED}❌ 健康检查失败 (HTTP ${HEALTH_CHECK})${NC}"
    echo "查看backend日志:"
    ssh ${SERVER_USER}@${SERVER_IP} "podman logs --tail 20 backend"
    exit 1
fi

# API Key路由检查
API_KEY_CHECK=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://${SERVER_IP}:8888/api/local-client/report-execution -H "Content-Type: application/json" -d '{"api_key":"test"}')
if [ "$API_KEY_CHECK" = "401" ]; then
    echo -e "${GREEN}✅ API Key路由正常 (HTTP 401 - 验证逻辑工作)${NC}"
else
    echo -e "${YELLOW}⚠️  API Key路由异常 (HTTP ${API_KEY_CHECK})${NC}"
fi

# 显示容器状态
echo ""
echo "容器状态:"
ssh ${SERVER_USER}@${SERVER_IP} "podman ps | grep -E 'backend|frontend'"

echo ""
echo "=========================================="
echo -e "${GREEN}🎉 部署完成！${NC}"
echo "=========================================="
echo ""
echo "访问地址:"
echo "  Web前端: http://${SERVER_IP}:8888"
echo "  API健康: http://${SERVER_IP}:8888/api/health"
echo ""
echo "如需查看日志:"
echo "  Backend: ssh root@${SERVER_IP} 'podman logs -f backend'"
echo "  Frontend: ssh root@${SERVER_IP} 'podman logs -f quantdinger-frontend'"
echo ""
