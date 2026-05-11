"""
WebSocket 连接测试脚本

测试 WebSocket 连接，无需运行完整后端。
"""

import asyncio
import json
from datetime import datetime, timezone

try:
    import websockets
    print("✓ websockets 库已安装")
except ImportError:
    print("✗ websockets 库未安装")
    print("请运行: pip install websockets")
    exit(1)


async def test_connection():
    """Test WebSocket connection."""
    
    print("\n" + "="*60)
    print("QuantDinger WebSocket 连接测试")
    print("="*60)
    
    # Test configuration
    api_key = "test-key-12345678"
    cloud_url = "ws://localhost:8765/ws"
    
    print(f"\n配置信息:")
    print(f"  API 密钥: {api_key}")
    print(f"  云端地址: {cloud_url}")
    print(f"\n正在尝试连接...")
    
    try:
        async with websockets.connect(cloud_url) as websocket:
            print("✓ 连接成功!")
            
            # Send authentication
            auth_message = {
                'api_key': api_key,
                'client_type': 'test_client',
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }
            await websocket.send(json.dumps(auth_message))
            print("✓ 认证信息已发送")
            
            # 等待响应
            print("\n等待服务器响应...")
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(response)
            
            print(f"\n✓ 服务器响应:")
            print(f"  类型: {data.get('type')}")
            print(f"  客户端 ID: {data.get('client_id', 'N/A')}")
            print(f"  消息: {data.get('message', 'N/A')}")
            
            if data.get('type') == 'connection_established':
                print("\n🎉 测试通过! WebSocket 连接正常工作。")
                return True
            else:
                print(f"\n⚠ 意外的响应类型: {data.get('type')}")
                return False
    
    except ConnectionRefusedError:
        print("\n✗ 连接被拒绝")
        print("\n可能原因:")
        print("  1. WebSocket 服务器未启动")
        print("  2. URL 或端口错误")
        print("\n启动服务器:")
        print("  cd backend_api_python")
        print("  python start_websocket_server.py")
        return False
    
    except asyncio.TimeoutError:
        print("\n✗ 连接超时")
        print("  服务器可能响应缓慢或无响应")
        return False
    
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    result = await test_connection()
    
    print("\n" + "="*60)
    if result:
        print("结果: ✓ 通过")
    else:
        print("结果: ✗ 失败")
    print("="*60 + "\n")
    
    return 0 if result else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    input("按回车键退出...")
    exit(exit_code)
