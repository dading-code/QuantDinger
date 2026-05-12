#!/usr/bin/env python3
"""
Check WebSocket server status and start it if needed
"""
import sys
import os
sys.path.insert(0, "/app")

from app.services.websocket_signal import get_signal_hub

print("=" * 80)
print("Checking WebSocket Hub Status")
print("=" * 80)

hub = get_signal_hub()
print(f"Hub initialized: {hub._initialized}")
print(f"Active connections: {hub.stats['active_connections']}")
print(f"Total connections: {hub.stats['total_connections']}")
print("=" * 80)
