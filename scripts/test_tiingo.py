#!/usr/bin/env python3
"""测试 Tiingo API 集成"""
import sys
import os
sys.path.insert(0, '/app')

print("=" * 60)
print("Testing Tiingo API Integration")
print("=" * 60)

# 检查环境变量
api_key = os.getenv('TIINGO_API_KEY', '')
print(f"\n1. Environment Check:")
print(f"   TIINGO_API_KEY configured: {bool(api_key)}")
print(f"   API Key (first 8): {api_key[:8] if api_key else 'N/A'}...")

if not api_key:
    print("\n❌ Tiingo API Key not configured!")
    sys.exit(1)

# 测试外汇数据
print("\n2. Testing Forex Data (EUR/USD)...")
try:
    from app.data_providers.forex import _fetch_tiingo
    
    pairs = [
        {"symbol": "EUR/USD", "tiingo": "eurusd"},
        {"symbol": "GBP/USD", "tiingo": "gbpusd"},
    ]
    
    result = _fetch_tiingo(pairs)
    print(f"   Result: {len(result)} pairs fetched")
    
    if result:
        for item in result:
            print(f"   - {item.get('symbol')}: ${item.get('last', 0):.4f}")
        print("   ✅ Success!")
    else:
        print("   ❌ No data returned")
        
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

# 测试贵金属数据
print("\n3. Testing Commodities (Gold/Silver)...")
try:
    from app.data_providers.commodities import _fetch_tiingo
    
    commodities = [
        {"name": "Gold", "symbol": "XAUUSD", "tiingo": "xauusd"},
        {"name": "Silver", "symbol": "XAGUSD", "tiingo": "xagusd"},
    ]
    
    result = _fetch_tiingo(commodities)
    print(f"   Result: {len(result)} commodities fetched")
    
    if result:
        for item in result:
            print(f"   - {item.get('name')} ({item.get('symbol')}): ${item.get('last', 0):.2f}")
        print("   ✅ Success!")
    else:
        print("   ❌ No data returned")
        
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

# 测试期货数据
print("\n4. Testing Futures (GC - Gold)...")
try:
    from app.data_sources.futures import FuturesDataSource
    
    ds = FuturesDataSource()
    ticker = ds.get_ticker('GC')  # 黄金期货
    
    if ticker and ticker.get('last', 0) > 0:
        print(f"   GC (Gold Future): ${ticker.get('last', 0):.2f}")
        print(f"   Source: {ticker.get('source', 'unknown')}")
        print("   ✅ Success!")
    else:
        print("   ❌ No data returned")
        
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test completed!")
print("=" * 60)
