#!/usr/bin/env python3
"""
Start WebSocket Signal Server alongside QuantDinger Backend

This script starts the WebSocket server for real-time signal broadcasting.
It should be run in addition to the main QuantDinger backend.

Usage:
    python start_websocket_server.py

The WebSocket server will listen on ws://0.0.0.0:8765/ws by default.
"""

import os
import sys
import asyncio

# Add backend_api_python to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_api_python'))

try:
    import websockets
except ImportError:
    print("ERROR: websockets library not installed")
    print("Install with: pip install websockets")
    sys.exit(1)

from app.services.websocket_signal import get_signal_hub, websocket_handler
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    """Start WebSocket server."""
    # Get configuration from environment variables
    host = os.getenv('WEBSOCKET_HOST', '0.0.0.0')
    port = int(os.getenv('WEBSOCKET_PORT', '8765'))
    
    hub = get_signal_hub()
    
    logger.info(f"Starting WebSocket Signal Server on ws://{host}:{port}/ws")
    logger.info("This server broadcasts trading signals to local trade executors")
    logger.info("")
    logger.info("Configuration:")
    logger.info(f"  Host: {host}")
    logger.info(f"  Port: {port}")
    logger.info(f"  Endpoint: ws://{host}:{port}/ws")
    logger.info("")
    logger.info("To connect:")
    logger.info("  1. Send auth message: {'api_key': 'your-api-key'}")
    logger.info("  2. Receive signals in real-time")
    logger.info("")
    logger.info("Local client example:")
    logger.info(f"  python scripts/local_trade_executor.py --api-key YOUR_KEY --cloud-url ws://{host}:{port}/ws")
    logger.info("")
    
    # Start WebSocket server
    async with websockets.serve(websocket_handler, host, port):
        logger.info("✓ WebSocket Signal Server started successfully")
        logger.info("Press Ctrl+C to stop")
        
        # Keep running
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nShutting down WebSocket Signal Server...")
    except Exception as e:
        logger.error(f"Failed to start WebSocket server: {e}")
        sys.exit(1)
