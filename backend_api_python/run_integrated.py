"""
集成启动脚本：同时启动 Flask 应用和 WebSocket 服务
解决进程间通信问题
"""
import os
import sys
import asyncio
import threading

# 设置路径
this_dir = os.path.dirname(os.path.abspath(__file__))
if this_dir not in sys.path:
    sys.path.insert(0, this_dir)

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(this_dir, ".env"), override=False)
except Exception:
    pass

def start_flask_app():
    """启动 Flask 应用"""
    from app import create_app
    from app.config.settings import Config
    
    print("🌐 启动 Flask 应用...")
    
    app = create_app()
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG,
        threaded=True,
        use_reloader=False  # 禁用自动重载，避免多进程问题
    )

async def start_websocket_server():
    """启动 WebSocket 服务"""
    import websockets
    from app.services.websocket_signal import websocket_handler
    
    host = os.getenv('WEBSOCKET_HOST', '0.0.0.0')
    port = int(os.getenv('WEBSOCKET_PORT', '8765'))
    
    print(f"🔌 启动 WebSocket 服务: ws://{host}:{port}")
    
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

def start_websocket():
    """在单独线程中启动 WebSocket 服务"""
    asyncio.run(start_websocket_server())

def main():
    print("=" * 60)
    print("🚀 QuantDinger 集成服务启动")
    print("=" * 60)
    
    # 启动 WebSocket 服务（在单独线程中）
    websocket_thread = threading.Thread(target=start_websocket, daemon=True)
    websocket_thread.start()
    
    # 等待 WebSocket 服务启动
    import time
    time.sleep(2)
    
    # 启动 Flask 应用
    start_flask_app()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"❌ 服务异常: {e}")
        import traceback
        traceback.print_exc()
