#!/bin/bash
# 测试API Key创建和credential_id关联功能

echo "=========================================="
echo "测试API Key和credential_id关联"
echo "=========================================="

# 1. 首先获取用户token（需要先用admin登录）
echo ""
echo "[1/5] 获取认证token..."
LOGIN_RESPONSE=$(curl -s -X POST http://39.105.150.99:8888/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}')

echo "登录响应: $LOGIN_RESPONSE"

# 提取token
TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data',{}).get('token',''))")

if [ -z "$TOKEN" ]; then
  echo "❌ 登录失败，无法获取token"
  exit 1
fi

echo "✅ Token获取成功"

# 2. 获取交易所配置列表（获取credential_id）
echo ""
echo "[2/5] 获取交易所配置列表..."
CREDENTIALS_RESPONSE=$(curl -s http://39.105.150.99:8888/api/credentials/list \
  -H "Authorization: Bearer $TOKEN")

echo "交易所配置响应:"
echo $CREDENTIALS_RESPONSE | python3 -m json.tool

# 提取第一个credential_id
CREDENTIAL_ID=$(echo $CREDENTIALS_RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); items=data.get('data',{}).get('items',[]); print(items[0]['id'] if items else '')")

if [ -z "$CREDENTIAL_ID" ]; then
  echo "❌ 没有找到交易所配置"
  exit 1
fi

echo "✅ 找到credential_id: $CREDENTIAL_ID"

# 3. 创建API Key（带credential_id）
echo ""
echo "[3/5] 创建API Key（关联credential_id=$CREDENTIAL_ID）..."
CREATE_RESPONSE=$(curl -s -X POST http://39.105.150.99:8888/api/users/api-key/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"key_name\": \"测试API Key\",
    \"description\": \"用于测试credential_id关联\",
    \"credential_id\": $CREDENTIAL_ID
  }")

echo "创建响应:"
echo $CREATE_RESPONSE | python3 -m json.tool

# 提取API Key
API_KEY=$(echo $CREATE_RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data',{}).get('api_key',''))")

if [ -z "$API_KEY" ]; then
  echo "❌ API Key创建失败"
  exit 1
fi

echo "✅ API Key创建成功: ${API_KEY:0:20}..."

# 4. 验证数据库中credential_id是否正确保存
echo ""
echo "[4/5] 验证数据库中credential_id..."
ssh root@39.105.150.99 << 'SSH_EOF'
podman exec backend python3 << 'PYEOF'
from app.utils.db import get_db_connection

with get_db_connection() as db:
    cur = db.cursor()
    
    # 查询最新的API Key
    cur.execute('''
        SELECT id, user_id, credential_id, key_name, active 
        FROM qd_api_keys 
        ORDER BY id DESC 
        LIMIT 1
    ''')
    row = cur.fetchone()
    
    if row:
        print(f"✅ 最新API Key:")
        print(f"   ID: {row['id']}")
        print(f"   User ID: {row['user_id']}")
        print(f"   Credential ID: {row['credential_id']}")
        print(f"   Key Name: {row['key_name']}")
        print(f"   Active: {row['active']}")
        
        if row['credential_id']:
            print("   ✅ credential_id已正确关联！")
        else:
            print("   ❌ credential_id为NULL，关联失败！")
    else:
        print("❌ 没有找到API Key记录")
    
    cur.close()
PYEOF
SSH_EOF

# 5. 验证list_credentials接口是否返回API Key信息
echo ""
echo "[5/5] 验证list_credentials接口..."
LIST_RESPONSE=$(curl -s http://39.105.150.99:8888/api/credentials/list \
  -H "Authorization: Bearer $TOKEN")

echo "凭证列表响应:"
echo $LIST_RESPONSE | python3 -m json.tool

echo ""
echo "=========================================="
echo "测试完成！"
echo "=========================================="
