# QuantDinger 一键部署脚本 v2.0 (PowerShell版本)
# 用途: 自动同步代码、更新容器、验证服务
# 使用: .\deploy_oneclick.ps1

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "QuantDinger 一键部署 v2.0 (PowerShell)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 配置
$SERVER_IP = "39.105.150.99"
$SERVER_USER = "root"
$PROJECT_DIR = "/opt/quantdinger/QuantDinger"
$LOCAL_BACKEND = "d:\www\workai\QuantDinger\backend_api_python"

# 步骤0: 检查SSH连接
Write-Host "[0/6] 检查SSH连接..." -ForegroundColor Yellow
try {
    $test = ssh -o ConnectTimeout=5 "${SERVER_USER}@${SERVER_IP}" "echo OK" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ SSH连接正常" -ForegroundColor Green
    } else {
        throw "SSH连接失败"
    }
} catch {
    Write-Host "❌ 无法连接到服务器 ${SERVER_IP}" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 步骤1: 上传后端代码到服务器
Write-Host "[1/6] 上传后端代码到服务器..." -ForegroundColor Yellow
Write-Host "  源目录: $LOCAL_BACKEND" -ForegroundColor Gray
Write-Host "  目标目录: ${SERVER_USER}@${SERVER_IP}:${PROJECT_DIR}/backend_api_python/" -ForegroundColor Gray

# 使用scp递归上传
$uploadCmd = "scp -r `"$LOCAL_BACKEND`" ${SERVER_USER}@${SERVER_IP}:${PROJECT_DIR}/"
Write-Host "  执行: $uploadCmd" -ForegroundColor Gray
Invoke-Expression $uploadCmd

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 代码上传成功" -ForegroundColor Green
} else {
    Write-Host "❌ 代码上传失败" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 步骤2: 复制代码到backend容器
Write-Host "[2/6] 复制代码到backend容器..." -ForegroundColor Yellow
ssh "${SERVER_USER}@${SERVER_IP}" @"
cd $PROJECT_DIR
podman cp backend_api_python backend:/app/backend_api_python
echo '✅ 代码已复制到容器'
"@
Write-Host ""

# 步骤3: 重启backend容器
Write-Host "[3/6] 重启backend容器..." -ForegroundColor Yellow
ssh "${SERVER_USER}@${SERVER_IP}" "podman restart backend"
Write-Host "✅ Backend容器已重启" -ForegroundColor Green
Write-Host ""

# 步骤4: 等待服务启动
Write-Host "[4/6] 等待服务启动（10秒）..." -ForegroundColor Yellow
Start-Sleep -Seconds 10
Write-Host "✅ 等待完成" -ForegroundColor Green
Write-Host ""

# 步骤5: 重启frontend刷新DNS
Write-Host "[5/6] 重启frontend容器（刷新DNS缓存）..." -ForegroundColor Yellow
ssh "${SERVER_USER}@${SERVER_IP}" "podman restart quantdinger-frontend"
Write-Host "✅ Frontend容器已重启" -ForegroundColor Green
Write-Host ""

# 步骤6: 验证服务
Write-Host "[6/6] 验证服务状态..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# 健康检查
Write-Host "  检查健康状态..." -ForegroundColor Gray
try {
    $response = Invoke-RestMethod -Uri "http://${SERVER_IP}:8888/api/health" -Method Get -TimeoutSec 5
    Write-Host "✅ 健康检查通过" -ForegroundColor Green
    Write-Host "  响应: $($response | ConvertTo-Json -Compress)" -ForegroundColor Gray
} catch {
    Write-Host "❌ 健康检查失败: $_" -ForegroundColor Red
    Write-Host "查看backend日志:" -ForegroundColor Yellow
    ssh "${SERVER_USER}@${SERVER_IP}" "podman logs --tail 20 backend"
    exit 1
}

# API Key路由检查
Write-Host "  检查API Key路由..." -ForegroundColor Gray
try {
    $body = @{api_key="test"} | ConvertTo-Json
    $response = Invoke-RestMethod -Uri "http://${SERVER_IP}:8888/api/local-client/report-execution" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 5
    Write-Host "⚠️  API Key路由返回意外结果" -ForegroundColor Yellow
} catch {
    if ($_.Exception.Response.StatusCode -eq 401) {
        Write-Host "✅ API Key路由正常 (HTTP 401 - 验证逻辑工作)" -ForegroundColor Green
    } else {
        Write-Host "⚠️  API Key路由异常: $($_.Exception.Response.StatusCode)" -ForegroundColor Yellow
    }
}

# 显示容器状态
Write-Host ""
Write-Host "容器状态:" -ForegroundColor Cyan
ssh "${SERVER_USER}@${SERVER_IP}" "podman ps | grep -E 'backend|frontend'"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "🎉 部署完成！" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "访问地址:" -ForegroundColor Cyan
Write-Host "  Web前端: http://${SERVER_IP}:8888" -ForegroundColor White
Write-Host "  API健康: http://${SERVER_IP}:8888/api/health" -ForegroundColor White
Write-Host ""
Write-Host "如需查看日志:" -ForegroundColor Cyan
Write-Host "  Backend: ssh root@${SERVER_IP} 'podman logs -f backend'" -ForegroundColor Gray
Write-Host "  Frontend: ssh root@${SERVER_IP} 'podman logs -f quantdinger-frontend'" -ForegroundColor Gray
Write-Host ""
