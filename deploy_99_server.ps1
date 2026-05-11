# 更新99服务器后端代码
# 包含API Key管理和WebSocket信号隔离功能

$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Green
Write-Host "QuantDinger 99服务器后端更新" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""

# 步骤1: SSH连接到99服务器
Write-Host "[1/5] 连接到99服务器..." -ForegroundColor Yellow
ssh root@39.105.150.99 @"
cd /root/QuantDinger

echo '当前Git状态:'
git status --short

echo ''
echo '拉取最新代码...'
git pull origin main

echo ''
echo '最新提交:'
git log --oneline -3
"@

if ($LASTEXITCODE -ne 0) {
    Write-Host "Git拉取失败！" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Git代码更新成功！" -ForegroundColor Green
Write-Host ""

# 步骤2: 检查数据库迁移
Write-Host "[2/5] 检查数据库迁移..." -ForegroundColor Yellow
ssh root@39.105.150.99 @"
cd /root/QuantDinger

echo '检查qd_api_keys表是否存在...'
podman exec backend python -c "
import psycopg2
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='quantdinger',
    user='quantdinger',
    password='quantdinger'
)
cur = conn.cursor()
cur.execute(\"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'qd_api_keys')\")
exists = cur.fetchone()[0]
cur.close()
conn.close()

if exists:
    print('✅ qd_api_keys表已存在')
else:
    print(' qd_api_keys表不存在，需要执行迁移')
"
"@

Write-Host ""

# 步骤3: 重新构建Docker镜像
Write-Host "[3/5] 重新构建Docker镜像..." -ForegroundColor Yellow
ssh root@39.105.150.99 @"
cd /root/QuantDinger

echo '停止现有容器...'
podman stop backend 2>/dev/null || true

echo '删除旧容器...'
podman rm backend 2>/dev/null || true

echo '构建新镜像...'
podman build -t localhost/quantdinger-backend:latest -f backend_api_python/Dockerfile .

echo '镜像构建完成！'
podman images | grep quantdinger-backend
"@

if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker构建失败！" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Docker镜像构建成功！" -ForegroundColor Green
Write-Host ""

# 步骤4: 启动新容器
Write-Host "[4/5] 启动新容器..." -ForegroundColor Yellow
ssh root@39.105.150.99 @"
cd /root/QuantDinger

echo '启动backend容器...'
podman run -d --name backend \
  --restart unless-stopped \
  -p 5000:5000 \
  -e FLASK_ENV=production \
  -e DATABASE_URL=postgresql://quantdinger:quantdinger@localhost:5432/quantdinger \
  -e REDIS_URL=redis://localhost:6379/0 \
  -v /root/QuantDinger/backend_api_python/logs:/app/logs \
  localhost/quantdinger-backend:latest

sleep 3

echo '检查容器状态...'
podman ps | grep backend

echo ''
echo '等待服务启动...'
sleep 5
"@

if ($LASTEXITCODE -ne 0) {
    Write-Host "容器启动失败！" -ForegroundColor Red
    exit 1
}

Write-Host "✅ 容器启动成功！" -ForegroundColor Green
Write-Host ""

# 步骤5: 测试API Key接口
Write-Host "[5/5] 测试API Key接口..." -ForegroundColor Yellow
ssh root@39.105.150.99 @"
echo '检查路由是否注册...'
podman exec backend python -c \"
from app import create_app
app = create_app()
rules = [str(rule) for rule in app.url_map.iter_rules() if 'api-key' in str(rule)]
if rules:
    print('✅ API Key路由已注册:')
    for rule in rules:
        print(f'  {rule}')
else:
    print('❌ API Key路由未注册')
\"
"@

Write-Host ""
Write-Host "=========================================" -ForegroundColor Green
Write-Host "✅ 99服务器后端更新完成！" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""
Write-Host "下一步：" -ForegroundColor Yellow
Write-Host "1. 在本地客户端重新测试登录和API Key创建" -ForegroundColor White
Write-Host "2. 检查日志确认API Key功能正常工作" -ForegroundColor White
Write-Host ""
