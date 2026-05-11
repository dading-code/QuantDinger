#!/usr/bin/env python3
"""
WebSocket Signal Client Test Script

This script tests the WebSocket connection to QuantDinger Cloud.
Use it to verify that your local client can receive signals properly.

Usage:
    python test_websocket_client.py --api-key YOUR_API_KEY --url ws://localhost:8765/ws
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime

try:
    import websockets
except ImportError:
    print("ERROR: websockets library not installed")
    print("Install with: pip install websockets")
    sys.exit(1)


async def test_connection(api_key: str, url: str):
    """Test WebSocket connection and listen for signals."""
    
    print("=" * 80)
    print("QuantDinger WebSocket Signal Client - Test Mode")
    print("=" * 80)
    print(f"\nConnecting to: {url}")
    print(f"API Key: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else '****'}")
    print("\nWaiting for signals... (Press Ctrl+C to stop)\n")
    
    try:
        async with websockets.connect(url) as websocket:
            # Send authentication
            auth_message = {
                "api_key": api_key,
                "client_type": "test_client",
                "timestamp": datetime.utcnow().isoformat(),
            }
            await websocket.send(json.dumps(auth_message))
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Authentication sent")
            
            # Wait for confirmation
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            data = json.loads(response)
            
            if data.get('type') == 'connection_established':
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Connected successfully!")
                print(f"  Client ID: {data.get('client_id')}")
                print(f"\nListening for trading signals...\n{'='*80}\n")
                
                # Listen for messages
                message_count = 0
                async for message in websocket:
                    message_count += 1
                    data = json.loads(message)
                    
                    print(f"\n{'='*80}")
                    print(f"[Message #{message_count}] Received at {datetime.now().strftime('%H:%M:%S')}")
                    print(f"Type: {data.get('type', 'unknown')}")
                    
                    if data.get('type') == 'trading_signal':
                        signal = data.get('data', {})
                        print(f"\n📊 Trading Signal Details:")
                        print(f"  Strategy: {signal.get('strategy_name', 'N/A')}")
                        print(f"  Symbol: {signal.get('symbol', 'N/A')}")
                        print(f"  Type: {signal.get('signal_type', 'N/A')}")
                        print(f"  Price: {signal.get('price', 0)}")
                        print(f"  Stake: {signal.get('stake_amount', 0)}")
                        print(f"  Direction: {signal.get('direction', 'N/A')}")
                        print(f"  Timestamp: {signal.get('timestamp', 'N/A')}")
                        
                        # Show notification results
                        notif_results = signal.get('notification_results', {})
                        if notif_results:
                            print(f"\n  Notification Results:")
                            for channel, result in notif_results.items():
                                status = "✓" if result.get('ok') else "✗"
                                error = f" ({result.get('error', '')})" if not result.get('ok') else ""
                                print(f"    {status} {channel}{error}")
                    
                    elif data.get('type') == 'pong':
                        print(f"  Heartbeat received")
                    
                    else:
                        print(f"\nFull message:")
                        print(json.dumps(data, indent=2, ensure_ascii=False))
                    
                    print(f"{'='*80}\n")
            
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Connection failed: {data}")
                return False
    
    except asyncio.TimeoutError:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✗ Connection timeout")
        return False
    
    except websockets.exceptions.ConnectionClosed as e:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✗ Connection closed: {e}")
        return False
    
    except Exception as e:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def main():
    parser = argparse.ArgumentParser(description='Test WebSocket Signal Client')
    parser.add_argument('--api-key', required=True, help='QuantDinger Cloud API key')
    parser.add_argument('--url', default='ws://localhost:8765/ws', help='WebSocket URL')
    
    args = parser.parse_args()
    
    success = await test_connection(args.api_key, args.url)
    
    if success:
        print("\n✓ Test completed successfully")
    else:
        print("\n✗ Test failed")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
