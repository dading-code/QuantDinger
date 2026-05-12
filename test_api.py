#!/usr/bin/env python3
"""
测试凭证列表API
"""
import requests
import json

# API地址
url = "http://39.105.150.99:8888/api/credentials/list"

# 需要登录后的session cookie或token
# 这里先尝试不带认证访问（应该会返回401）
try:
    response = requests.get(url)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
