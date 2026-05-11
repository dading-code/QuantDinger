"""
端到端测试：验证用户信号隔离

测试场景：
1. 创建两个测试用户（user_a, user_b）
2. 为每个用户生成API Key
3. 启动两个WebSocket客户端分别连接
4. 发送属于user_a的信号，验证只有user_a的客户端收到
5. 发送属于user_b的信号，验证只有user_b的客户端收到
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_api_python'))

from app.services.api_key_manager import APIKeyService
from app.services.websocket_signal import WebSocketSignalHub
from app.utils.db import get_db_connection


async def test_user_isolation():
    """Test that signals are properly isolated between users."""
    
    print("=" * 80)
    print("开始端到端测试：用户信号隔离")
    print("=" * 80)
    
    # Step 1: Find or create test users
    print("\n[步骤 1] 查找测试用户...")
    
    with get_db_connection() as db:
        cur = db.cursor()
        
        # Check if test users exist
        cur.execute("SELECT id, username FROM qd_users WHERE username IN ('trader01', 'testuser') LIMIT 2")
        users = cur.fetchall()
        cur.close()
    
    if len(users) < 2:
        print("✗ 错误：需要至少2个测试用户（trader01, testuser）")
        print("请先在系统中创建这些用户")
        return False
    
    user_a = users[0]
    user_b = users[1]
    
    print(f"✓ 找到用户A: {user_a['username']} (ID: {user_a['id']})")
    print(f"✓ 找到用户B: {user_b['username']} (ID: {user_b['id']})")
    
    # Step 2: Create API keys for each user
    print("\n[步骤 2] 为用户生成API Key...")
    
    result_a = APIKeyService.create_api_key(
        user_id=user_a['id'],
        key_name='E2E_Test_UserA',
        description='End-to-end test for user A',
        expires_days=1
    )
    
    result_b = APIKeyService.create_api_key(
        user_id=user_b['id'],
        key_name='E2E_Test_UserB',
        description='End-to-end test for user B',
        expires_days=1
    )
    
    api_key_a = result_a['api_key']
    api_key_b = result_b['api_key']
    
    print(f"✓ 用户A API Key: {api_key_a[:20]}...")
    print(f"✓ 用户B API Key: {api_key_b[:20]}...")
    
    # Step 3: Initialize WebSocket hub
    print("\n[步骤 3] 初始化WebSocket Hub...")
    
    hub = WebSocketSignalHub()
    await hub.initialize()
    print("✓ WebSocket Hub已初始化")
    
    # Step 4: Simulate client connections
    print("\n[步骤 4] 模拟客户端连接...")
    
    # Create mock websockets
    class MockWebSocket:
        def __init__(self, name):
            self.name = name
            self.messages = []
            self.remote_address = ('127.0.0.1', 8080)
        
        async def send(self, message):
            self.messages.append(message)
            print(f"  [{self.name}] 收到消息: {message[:100]}...")
        
        async def close(self, code=None, reason=None):
            print(f"  [{self.name}] 连接关闭: {reason}")
    
    ws_a = MockWebSocket("Client_A")
    ws_b = MockWebSocket("Client_B")
    
    # Register clients
    await hub.register_client(ws_a, api_key_a)
    await hub.register_client(ws_b, api_key_b)
    
    print(f"✓ 客户端A已注册 (用户: {user_a['username']})")
    print(f"✓ 客户端B已注册 (用户: {user_b['username']})")
    print(f"✓ 当前活跃连接数: {hub.stats['active_connections']}")
    
    # Step 5: Send signal to user A only
    print("\n[步骤 5] 发送信号给用户A...")
    
    signal_for_a = {
        'strategy_name': 'TestStrategy',
        'symbol': 'AAPL',
        'signal_type': 'buy',
        'price': 150.0,
        'user_id': user_a['id']  # Target user A
    }
    
    await hub.broadcast_signal(signal_for_a, target_user_id=user_a['id'])
    
    # Verify only client A received the signal
    if len(ws_a.messages) == 2 and len(ws_b.messages) == 1:  # A got welcome + signal, B got only welcome
        print("✓ 测试通过：只有用户A的客户端收到了信号")
    else:
        print(f"✗ 测试失败：")
        print(f"  客户端A收到 {len(ws_a.messages)} 条消息")
        print(f"  客户端B收到 {len(ws_b.messages)} 条消息")
        return False
    
    # Step 6: Send signal to user B only
    print("\n[步骤 6] 发送信号给用户B...")
    
    signal_for_b = {
        'strategy_name': 'TestStrategy',
        'symbol': 'GOOGL',
        'signal_type': 'sell',
        'price': 2800.0,
        'user_id': user_b['id']  # Target user B
    }
    
    await hub.broadcast_signal(signal_for_b, target_user_id=user_b['id'])
    
    # Verify only client B received the signal
    if len(ws_a.messages) == 2 and len(ws_b.messages) == 2:
        print("✓ 测试通过：只有用户B的客户端收到了信号")
    else:
        print(f"✗ 测试失败：")
        print(f"  客户端A收到 {len(ws_a.messages)} 条消息")
        print(f"  客户端B收到 {len(ws_b.messages)} 条消息")
        return False
    
    # Step 7: Send broadcast signal (to all users)
    print("\n[步骤 7] 发送广播信号（所有用户）...")
    
    broadcast_signal = {
        'strategy_name': 'BroadcastStrategy',
        'symbol': 'SPY',
        'signal_type': 'buy',
        'price': 450.0
    }
    
    await hub.broadcast_signal(broadcast_signal, target_user_id=None)
    
    # Verify both clients received the broadcast
    if len(ws_a.messages) == 3 and len(ws_b.messages) == 3:
        print("✓ 测试通过：所有客户端都收到了广播信号")
    else:
        print(f"✗ 测试失败：")
        print(f"  客户端A收到 {len(ws_a.messages)} 条消息")
        print(f"  客户端B收到 {len(ws_b.messages)} 条消息")
        return False
    
    # Step 8: Cleanup
    print("\n[步骤 8] 清理测试数据...")
    
    await hub.unregister_client(list(hub.clients.keys())[0])
    await hub.unregister_client(list(hub.clients.keys())[0])
    
    # Revoke API keys
    APIKeyService.revoke_api_key(user_a['id'], result_a['key_info']['id'])
    APIKeyService.revoke_api_key(user_b['id'], result_b['key_info']['id'])
    
    print("✓ 测试数据已清理")
    
    # Final summary
    print("\n" + "=" * 80)
    print("✅ 所有测试通过！")
    print("=" * 80)
    print("\n测试结果总结：")
    print("  ✓ 用户A只能接收自己的信号")
    print("  ✓ 用户B只能接收自己的信号")
    print("  ✓ 广播信号可以发送给所有用户")
    print("  ✓ 用户隔离机制工作正常")
    print("=" * 80)
    
    return True


if __name__ == '__main__':
    try:
        success = asyncio.run(test_user_isolation())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
