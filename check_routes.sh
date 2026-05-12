#!/bin/bash
# 检查API Key路由是否注册

echo "检查API Key相关路由："
podman exec backend python3 << 'EOF'
from app import create_app
app = create_app()
rules = [rule.rule for rule in app.url_map.iter_rules()]
api_key_rules = [r for r in rules if 'api-key' in r or 'local-client' in r]
print("找到的路由:", api_key_rules)
EOF
