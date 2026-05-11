#!/bin/bash
# 检查99服务器上API Key路由是否存在

echo "=========================================="
echo "检查API Key路由"
echo "=========================================="

# 进入容器执行Python代码
podman exec backend python3 << 'EOF'
from app import create_app
app = create_app()

print("\n查找包含 'api-key' 的路由:")
print("-" * 60)

found = False
for rule in app.url_map.iter_rules():
    if 'api-key' in str(rule):
        print(f"✅ {rule}")
        found = True

if not found:
    print("❌ 未找到任何 api-key 路由")
    print("\n所有 /api/users/ 路由:")
    for rule in app.url_map.iter_rules():
        if '/api/users/' in str(rule):
            print(f"  {rule}")
else:
    print(f"\n✅ 找到 {sum(1 for r in app.url_map.iter_rules() if 'api-key' in str(r))} 个 API Key 路由")

EOF

echo ""
echo "=========================================="
echo "测试API Key接口"
echo "=========================================="

# 测试健康检查
echo -n "健康检查: "
curl -s http://localhost:5000/api/health | head -c 100
echo ""

# 测试API Key列表（应该返回401，说明路由存在）
echo -n "API Key列表接口: "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/api/users/api-key/list)
echo "HTTP $HTTP_CODE"

if [ "$HTTP_CODE" = "401" ]; then
    echo "✅ 路由存在（需要认证）"
elif [ "$HTTP_CODE" = "404" ]; then
    echo "❌ 路由不存在（404）"
else
    echo "⚠️  unexpected response: HTTP $HTTP_CODE"
fi
