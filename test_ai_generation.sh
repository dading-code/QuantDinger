#!/bin/bash
echo "========================================"
echo "测试AI生成功能"
echo "========================================"
echo ""

# 先登录获取token
echo "[步骤1] 登录获取token..."
LOGIN_RESPONSE=$(curl -s -X POST http://39.105.150.99:8888/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"123456"}')

echo "登录响应: $LOGIN_RESPONSE"

# 提取token（使用python解析JSON）
TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "❌ 无法获取token"
    exit 1
fi

echo "✅ Token获取成功"
echo ""

# 测试AI生成策略
echo "[步骤2] 测试AI生成策略..."
AI_RESPONSE=$(curl -s -X POST http://39.105.150.99:8888/api/strategies/ai-generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "market": "Crypto",
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "strategy_type": "IndicatorStrategy",
    "description": "创建一个简单的双均线策略"
  }')

echo "AI生成响应:"
echo "$AI_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$AI_RESPONSE"

echo ""
echo "========================================"
echo "测试完成"
echo "========================================"
