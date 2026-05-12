# 测试API Key创建接口
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "测试API Key创建接口" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. 登录获取token
Write-Host "`n[1/3] 登录..." -ForegroundColor Yellow
$loginBody = @{username="admin"; password="admin123"} | ConvertTo-Json
try {
    $loginResponse = Invoke-RestMethod -Uri "http://39.105.150.99:8888/api/auth/login" -Method Post -ContentType "application/json" -Body $loginBody
    
    if ($loginResponse.code -ne 1) {
        Write-Host "❌ 登录失败: $($loginResponse.msg)" -ForegroundColor Red
        exit 1
    }
    
    $token = $loginResponse.data.token
    Write-Host "✅ Token: $($token.Substring(0, [Math]::Min(20, $token.Length)))..." -ForegroundColor Green
} catch {
    Write-Host "❌ 登录请求失败: $_" -ForegroundColor Red
    exit 1
}

# 2. 获取credential_id
Write-Host "`n[2/3] 获取credential_id..." -ForegroundColor Yellow
$headers = @{Authorization = "Bearer $token"}
try {
    $credentialsResponse = Invoke-RestMethod -Uri "http://39.105.150.99:8888/api/credentials/list" -Method Get -Headers $headers
    
    $items = $credentialsResponse.data.items
    if (-not $items -or $items.Count -eq 0) {
        Write-Host "❌ 没有找到交易所配置" -ForegroundColor Red
        exit 1
    }
    
    $credentialId = $items[0].id
    Write-Host "✅ credential_id: $credentialId" -ForegroundColor Green
} catch {
    Write-Host "❌ 获取凭证列表失败: $_" -ForegroundColor Red
    exit 1
}

# 3. 创建API Key（带credential_id）
Write-Host "`n[3/3] 创建API Key（关联credential_id=$credentialId）..." -ForegroundColor Yellow
$createBody = @{
    key_name = "测试Key"
    description = "测试"
    credential_id = $credentialId
} | ConvertTo-Json

try {
    $createResponse = Invoke-RestMethod -Uri "http://39.105.150.99:8888/api/users/api-key/create" -Method Post -Headers $headers -ContentType "application/json" -Body $createBody
    
    Write-Host "响应: $($createResponse | ConvertTo-Json -Depth 10)" -ForegroundColor Gray
    
    if ($createResponse.code -eq 1) {
        Write-Host "✅ API Key创建成功！" -ForegroundColor Green
        
        $apiKey = $createResponse.data.api_key
        Write-Host "API Key: $($apiKey.Substring(0, [Math]::Min(20, $apiKey.Length)))..." -ForegroundColor Cyan
        
        $returnedCredId = $createResponse.data.key_info.credential_id
        Write-Host "返回的credential_id: $returnedCredId" -ForegroundColor Cyan
        
        if ($returnedCredId -eq $credentialId) {
            Write-Host "✅ credential_id正确关联！" -ForegroundColor Green
        } else {
            Write-Host "❌ credential_id关联错误！期望:$credentialId, 实际:$returnedCredId" -ForegroundColor Red
        }
    } else {
        Write-Host "❌ API Key创建失败: $($createResponse.msg)" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ 创建API Key请求失败: $_" -ForegroundColor Red
}

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "测试完成！" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
