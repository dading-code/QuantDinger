#!/bin/bash
# 简单测试API Key创建接口

echo "=========================================="
echo "测试API Key创建接口"
echo "=========================================="

# 1. 登录获取token
echo ""
echo "[1/3] 登录..."
TOKEN=$(curl -s -X POST http://39.105.150.99:8888/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys, json; print(json.load(sys.stdin).get('data',{}).get('token',''))")

if [ -z "$TOKEN" ]; then
  echo "❌ 登录失败"
  exit 1
fi

echo "✅ Token: ${TOKEN:0:20}..."

# 2. 获取credential_id
echo ""
echo "[2/3] 获取credential_id..."
CREDENTIAL_ID=$(curl -s http://39.105.150.99:8888/api/credentials/list \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; items=json.load(sys.stdin).get('data',{}).get('items',[]); print(items[0]['id'] if items else '')")

if [ -z "$CREDENTIAL_ID" ]; then
  echo "❌ 没有找到交易所配置"
  exit 1
fi

echo "✅ credential_id: $CREDENTIAL_ID"

# 3. 创建API Key（带credential_id）
echo ""
echo "[3/3] 创建API Key（关联credential_id=$CREDENTIAL_ID）..."
RESPONSE=$(curl -s -X POST http://39.105.150.99:8888/api/users/api-key/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"key_name\":\"测试Key\",\"description\":\"测试\",\"credential_id\":$CREDENTIAL_ID}")

echo "响应: $RESPONSE"

# 检查是否成功
SUCCESS=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('code',0))")

if [ "$SUCCESS" = "1" ]; then
  echo "✅ API Key创建成功！"
  
  # 提取API Key
  API_KEY=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('data',{}).get('api_key',''))")
  echo "API Key: ${API_KEY:0:20}..."
  
  # 检查返回的credential_id
  RETURNED_CRED_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('data',{}).get('key_info',{}).get('credential_id',''))")
  echo "返回的credential_id: $RETURNED_CRED_ID"
  
  if [ "$RETURNED_CRED_ID" = "$CREDENTIAL_ID" ]; then
    echo "✅ credential_id正确关联！"
  else
    echo "❌ credential_id关联错误！期望:$CREDENTIAL_ID, 实际:$RETURNED_CRED_ID"
  fi
else
  echo "❌ API Key创建失败"
  echo "错误信息: $(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('msg',''))")"
fi

echo ""
echo "=========================================="
echo "测试完成！"
echo "=========================================="
