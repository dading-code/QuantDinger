"""
单独启动 WebSocket 服务的脚本

使用方法：
python run_websocket_only.py
"""
import os
import sys

# 确保 backend_api_python 目录在 sys.path 中
this_dir = os.path.dirname(os.path.abspath(__file__))
if this_dir not in sys.path:
    sys.path.insert(0, this_dir)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(this_dir, ".env"), override=False)
except Exception:
    pass

import asyncio
import websockets
from app.services.websocket_signal import websocket_handler

def main():
    host = os.getenv('WEBSOCKET_HOST', '0.0.0.0')
    port = int(os.getenv('WEBSOCKET_PORT', '8765'))
    
    print(f"🚀 启动 WebSocket 服务: ws://{host}:{port}")
    
    async def start_server():
        async with websockets.serve(
            websocket_handler,
            host,
            port,
            ping_interval=30,
            ping_timeout=10,
        ) as server:
            print(f"✅ WebSocket 服务已启动: ws://{host}:{port}")
            print(f"   Observer 连接地址: ws://{host}:{port}/ws/v1/agent/{{account_id}}?token={{token}}")
            await asyncio.Future()  # Run forever
    
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        print("\n👋 WebSocket 服务已停止")
    except Exception as e:
        print(f"❌ WebSocket 服务异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
