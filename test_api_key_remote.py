"""
测试API Key接口 - 直接测试99服务器
"""

import requests
import json
import sys

# 配置
BASE_URL = "http://39.105.150.99:8888/api"
USERNAME = "testuser"
PASSWORD = "testuser123"

def test_login():
    """测试登录"""
    print("\n" + "="*60)
    print("测试1: 用户登录")
    print("="*60)
    
    url = f"{BASE_URL}/auth/login"
    data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    
    print(f"URL: {url}")
    print(f"数据: {json.dumps(data, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, json=data, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text[:500]}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 1:
                token = result['data'].get('token')
                print(f"\n✅ 登录成功！")
                print(f"Token: {token[:30]}...")
                return token
            else:
                print(f"\n❌ 登录失败: {result.get('msg')}")
                return None
        else:
            print(f"\n❌ HTTP错误: {response.status_code}")
            print(f"响应: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ 连接错误: 无法连接到 {BASE_URL}")
        print(f"错误: {e}")
        return None
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        return None

def test_create_api_key(token):
    """测试创建API Key"""
    print("\n" + "="*60)
    print("测试2: 创建API Key")
    print("="*60)
    
    url = f"{BASE_URL}/users/api-key/create"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "key_name": "TestLocalClient",
        "description": "本地测试客户端",
        "expires_days": 365
    }
    
    print(f"URL: {url}")
    print(f"Headers: Authorization=Bearer {token[:20]}...")
    print(f"数据: {json.dumps(data, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text[:500]}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 1:
                api_key = result['data'].get('api_key')
                print(f"\n✅ API Key创建成功！")
                print(f"API Key: {api_key}")
                return api_key
            else:
                print(f"\n❌ 创建失败: {result.get('msg')}")
                return None
        else:
            print(f"\n❌ HTTP错误: {response.status_code}")
            print(f"响应: {response.text}")
            
            # 检查是否是404
            if response.status_code == 404:
                print("\n 404错误说明：")
                print("   - 服务器上没有/api/users/api-key/create路由")
                print("   - 99服务器需要更新后端代码")
                return None
                
            return None
            
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        return None

def test_old_url(token):
    """测试旧URL路径"""
    print("\n" + "="*60)
    print("测试3: 测试旧URL路径 (/user/)")
    print("="*60)
    
    url = f"{BASE_URL}/user/api-key/create"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "key_name": "TestOldUrl",
        "description": "测试旧URL",
        "expires_days": 365
    }
    
    print(f"URL: {url}")
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text[:300]}")
        
        if response.status_code == 404:
            print("\n❌ 旧URL也返回404，确认路由不存在")
        elif response.status_code == 200:
            print("\n✅ 旧URL可用！")
            
    except Exception as e:
        print(f"\n❌ 异常: {e}")

def main():
    print("\n" + "="*60)
    print("QuantDinger API Key 接口测试")
    print(f"目标服务器: {BASE_URL}")
    print("="*60)
    
    # 测试1: 登录
    token = test_login()
    if not token:
        print("\n❌ 登录失败，无法继续测试")
        sys.exit(1)
    
    # 测试2: 创建API Key (新URL)
    api_key = test_create_api_key(token)
    
    # 测试3: 测试旧URL
    test_old_url(token)
    
    print("\n" + "="*60)
    if api_key:
        print("✅ 测试完成！API Key创建成功")
    else:
        print("❌ API Key创建失败")
        print("\n建议：")
        print("1. 检查99服务器是否已更新到最新代码")
        print("2. 确认后端包含API Key管理路由")
        print("3. 执行部署脚本: .\\deploy_99_server.ps1")
    print("="*60)

if __name__ == "__main__":
    main()
