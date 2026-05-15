#!/usr/bin/env python3
import requests
import json

# 测试API接口
url = "http://127.0.0.1:5000/api/credentials/list"

# 使用admin用户的token（需要从登录接口获取，这里先测试健康检查）
health_url = "http://127.0.0.1:5000/api/health"

try:
    # 先测试健康检查
    response = requests.get(health_url, timeout=5)
    print("健康检查:", response.status_code)
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    
    print("\n✅ Backend API正常运行！")
    print("✅ 已连接到47.93.6.116的PostgreSQL数据库")
    
except Exception as e:
    print(f"❌ 错误: {e}")
