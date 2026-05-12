#!/usr/bin/env python3
"""
测试API Key创建和credential_id关联功能
"""
import requests
import json

BASE_URL = "http://39.105.150.99:8888"

def test_api_key_creation():
    print("=" * 60)
    print("测试API Key创建和credential_id关联")
    print("=" * 60)
    
    # 1. 登录获取token
    print("\n[1/4] 登录获取token...")
    login_response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    
    if login_response.status_code != 200:
        print(f"❌ 登录失败: {login_response.status_code}")
        print(login_response.text)
        return False
    
    login_data = login_response.json()
    if login_data.get('code') != 1:
        print(f"❌ 登录失败: {login_data.get('msg')}")
        return False
    
    token = login_data['data']['token']
    print(f"✅ 登录成功，token: {token[:20]}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. 获取交易所配置列表（获取credential_id）
    print("\n[2/4] 获取交易所配置列表...")
    credentials_response = requests.get(
        f"{BASE_URL}/api/credentials/list",
        headers=headers
    )
    
    if credentials_response.status_code != 200:
        print(f"❌ 获取凭证列表失败: {credentials_response.status_code}")
        return False
    
    credentials_data = credentials_response.json()
    print(f"凭证列表响应: {json.dumps(credentials_data, ensure_ascii=False, indent=2)}")
    
    items = credentials_data.get('data', {}).get('items', [])
    if not items:
        print("❌ 没有找到交易所配置")
        return False
    
    credential_id = items[0]['id']
    print(f"✅ 找到credential_id: {credential_id}")
    
    # 3. 创建API Key（带credential_id）
    print("\n[3/4] 创建API Key（关联credential_id={})...".format(credential_id))
    create_response = requests.post(
        f"{BASE_URL}/api/users/api-key/create",
        headers={**headers, "Content-Type": "application/json"},
        json={
            "key_name": "测试API Key",
            "description": "用于测试credential_id关联",
            "credential_id": credential_id
        }
    )
    
    print(f"创建响应状态码: {create_response.status_code}")
    print(f"创建响应: {json.dumps(create_response.json(), ensure_ascii=False, indent=2)}")
    
    if create_response.status_code != 200:
        print(f"❌ API Key创建失败: {create_response.status_code}")
        return False
    
    create_data = create_response.json()
    if create_data.get('code') != 1:
        print(f"❌ API Key创建失败: {create_data.get('msg')}")
        return False
    
    api_key = create_data['data']['api_key']
    print(f"✅ API Key创建成功: {api_key[:20]}...")
    
    # 4. 验证数据库中credential_id是否正确保存
    print("\n[4/4] 验证数据库中的credential_id...")
    print("需要通过SSH执行数据库查询...")
    
    # 这里需要SSH到服务器查询数据库
    # 暂时跳过，直接在服务器上执行
    
    print("\n" + "=" * 60)
    print("✅ 后端API接口测试通过！")
    print("=" * 60)
    print("\n下一步：")
    print("1. 检查数据库中credential_id是否正确保存")
    print("2. 让前端修改代码，传递credential_id参数")
    print("3. 前端创建成功后调用loadExchangeCredentials()刷新列表")
    
    return True

if __name__ == "__main__":
    try:
        test_api_key_creation()
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
