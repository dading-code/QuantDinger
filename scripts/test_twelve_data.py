#!/usr/bin/env python3
"""测试Twelve Data集成"""
import sys
import os
sys.path.insert(0, '/app')

print("Environment check:")
print(f"  TWELVE_DATA_API_KEY set: {bool(os.getenv('TWELVE_DATA_API_KEY'))}")
print(f"  API Key (first 8): {os.getenv('TWELVE_DATA_API_KEY', 'NOT SET')[:8] if os.getenv('TWELVE_DATA_API_KEY') else 'N/A'}")
print()

from app.data_sources.us_stock import USStockDataSource, _fetch_twelvedata_kline

print("=" * 60)
print("Testing Twelve Data Integration for US Stocks")
print("=" * 60)

# 创建数据源实例
ds = USStockDataSource()

# 测试转换函数
print("\n1. Testing interval conversion...")
test_intervals = ['1d', '1D', '1h', '1H', '5m']
for interval in test_intervals:
    td_interval = ds._convert_to_td_interval(interval)
    print(f"   {interval} -> {td_interval}")

# 直接测试_fetch_twelvedata_kline函数
print("\n2. Testing _fetch_twelvedata_kline directly...")
klines = _fetch_twelvedata_kline('AAPL', '1day', 5)
print(f"   Result: {len(klines)} bars")
if klines:
    print(f"   Latest: {klines[-1]}")

# 测试获取AAPL日线数据
print("\n3. Testing get_kline method...")
klines = ds.get_kline('AAPL', '1D', 5)

if klines:
    print(f"   ✅ Success! Fetched {len(klines)} bars")
    print(f"   Latest bar:")
    print(f"     Time: {klines[-1]['time']}")
    print(f"     Close: ${klines[-1]['close']}")
else:
    print("   ❌ Failed - No data returned")

print("\n" + "=" * 60)
print("Test completed!")
print("=" * 60)
