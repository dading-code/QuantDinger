"""Gunicorn configuration for QuantDinger backend.

Background workers (strategy restore, portfolio monitor, etc.) are started
inside ``create_app()`` which is called once per worker.  We use gthread
(threads in a single worker) by default to keep a familiar single-process
model while still allowing concurrent I/O.  Increase ``workers`` for
higher throughput — background tasks are idempotent and use DB locks to
coordinate, so duplicate work is minimal.
"""
import os
import sys
import threading
import time
import signal

bind = f"{os.getenv('PYTHON_API_HOST', '0.0.0.0')}:{os.getenv('PYTHON_API_PORT', '5000')}"

# Default: 1 worker + 4 threads — same concurrency model as Flask dev server
# but with better stability and connection handling.
# Increase GUNICORN_WORKERS for multi-core throughput.
workers = int(os.getenv("GUNICORN_WORKERS", 1))
threads = int(os.getenv("GUNICORN_THREADS", 4))

worker_class = "gthread"
timeout = 120
graceful_timeout = 30
keepalive = 5

# Do NOT preload — background threads in create_app() rely on being in
# the actual worker process.  preload would start them in master then
# lose them after fork.
preload_app = False

accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")

limit_request_line = 8190
limit_request_fields = 100

# WebSocket server integration
_ws_started = False
_ws_thread = None


def _load_env_file(env_path):
    """Manually load .env file as key=value pairs."""
    if not os.path.exists(env_path):
        return
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key not in os.environ:  # Don't override existing env vars
                    os.environ[key] = value


def on_starting(server):
    """
    Gunicorn hook: called once when the master process starts.
    We use this to launch the WebSocket signal server in a background thread.
    """
    global _ws_started, _ws_thread
    
    if _ws_started:
        return
    
    # Load .env file here since gunicorn config is evaluated before run.py
    this_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(this_dir, '.env')
    try:
        # Try dotenv first
        from dotenv import load_dotenv
        load_dotenv(env_path, override=False)
        print(f"[WebSocket] Loaded .env via dotenv from {env_path}", flush=True)
    except ImportError:
        # Fallback to manual loading
        _load_env_file(env_path)
        print(f"[WebSocket] Loaded .env manually from {env_path}", flush=True)
    except Exception as e:
        _load_env_file(env_path)
        print(f"[WebSocket] Loaded .env via fallback from {env_path} (dotenv error: {e})", flush=True)
    
    _ws_started = True
    
    try:
        print("="*50, flush=True)
        print("[WebSocket] Initializing WebSocket signal server...", flush=True)
        
        # Start WebSocket server in background thread
        _ws_thread = threading.Thread(
            target=_start_websocket_server,
            daemon=True,  # Daemon thread will exit when main process exits
            name="WebSocketSignalServer"
        )
        _ws_thread.start()
        
        print("[WebSocket] WebSocket server started in background (port 8765)", flush=True)
        print("="*50, flush=True)
        
    except Exception as e:
        print(f"[WebSocket] ERROR: Failed to start WebSocket server: {e}", flush=True)


def _start_websocket_server():
    """
    Start the WebSocket signal server in a background thread.
    This runs independently from the Gunicorn worker processes.
    """
    try:
        # Ensure the backend_api_python directory is in sys.path
        # This is critical for the background thread to find the app module
        this_dir = os.path.dirname(os.path.abspath(__file__))
        if this_dir not in sys.path:
            sys.path.insert(0, this_dir)
        
        import asyncio
        import websockets
        from app.services.websocket_signal import websocket_handler
        
        host = os.getenv('WEBSOCKET_HOST', '0.0.0.0')
        port = int(os.getenv('WEBSOCKET_PORT', '8765'))
        
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def start_server():
            async with websockets.serve(
                websocket_handler,
                host,
                port,
                ping_interval=30,
                ping_timeout=10,
            ) as server:
                print(f"[WebSocket] Signal server listening on {host}:{port}", flush=True)
                await asyncio.Future()  # Run forever
        
        # Run the async server in this thread's event loop
        loop.run_until_complete(start_server())
        
    except Exception as e:
        print(f"[WebSocket] Server error: {e}", flush=True)
        import traceback
        traceback.print_exc()
