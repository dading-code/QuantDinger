"""
本地测试：API Key创建功能
测试登录和API Key创建流程
"""

import requests
import json
import sys
import os

# 配置
BASE_URL = "http://localhost:5000/api"
TEST_USERNAME = "testuser"
TEST_PASSWORD = "testuser123"

def test_login():
    """测试登录"""
    print("\n" + "="*60)
    print("测试1: 用户登录")
    print("="*60)
    
    url = f"{BASE_URL}/auth/login"
    data = {
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 1:
                token = result['data'].get('token')
                print(f"\n✅ 登录成功！Token: {token[:20]}...")
                return token
            else:
                print(f"\n❌ 登录失败: {result.get('msg')}")
                return None
        else:
            print(f"\n❌ HTTP错误: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        return None

def test_create_api_key(token):
    """测试创建API Key"""
    print("\n" + "="*60)
    print("测试2: 创建API Key")
    print("="*60)
    
    url = f"{BASE_URL}/user/api-key/create"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "key_name": "TestLocalClient",
        "description": "本地测试客户端",
        "expires_days": 365
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 1:
                api_key = result['data'].get('api_key')
                print(f"\n✅ API Key创建成功！")
                print(f"API Key: {api_key}")
                print(f"密钥名称: {result['data'].get('key_name')}")
                print(f"过期时间: {result['data'].get('expires_at')}")
                return api_key
            else:
                print(f"\n❌ 创建失败: {result.get('msg')}")
                return None
        else:
            print(f"\n❌ HTTP错误: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        return None

def test_list_api_keys(token):
    """测试获取API Key列表"""
    print("\n" + "="*60)
    print("测试3: 获取API Key列表")
    print("="*60)
    
    url = f"{BASE_URL}/user/api-key/list"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200 and result.get('code') == 1:
            keys = result['data'].get('keys', [])
            print(f"\n✅ 找到 {len(keys)} 个API Key")
            for key in keys:
                print(f"  - {key.get('key_name')} (ID: {key.get('id')}, 状态: {'活跃' if key.get('active') else '已停用'})")
            return True
        else:
            print(f"\n❌ 获取失败")
            return False
            
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("QuantDinger API Key 功能本地测试")
    print("="*60)
    
    # 测试1: 登录
    token = test_login()
    if not token:
        print("\n 登录失败，无法继续测试")
        sys.exit(1)
    
    # 测试2: 创建API Key
    api_key = test_create_api_key(token)
    if not api_key:
        print("\n❌ API Key创建失败")
        sys.exit(1)
    
    # 测试3: 获取API Key列表
    test_list_api_keys(token)
    
    print("\n" + "="*60)
    print("✅ 所有测试通过！")
    print("="*60)

if __name__ == "__main__":
    main()
