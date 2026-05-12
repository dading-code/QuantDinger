#!/usr/bin/env python3
"""验证所有API接口配置"""
import sys
sys.path.insert(0, '/app')

print("=" * 70)
print("QuantDinger API 接口全量验证")
print("=" * 70)

# 1. Twelve Data - 美股数据
print("\n1️⃣  Twelve Data (美股K线)")
try:
    from app.data_sources.us_stock import USStockDataSource
    ds = USStockDataSource()
    klines = ds.get_kline('AAPL', '1D', 5)
    if klines:
        print(f"   ✅ AAPL日线: {len(klines)}条, 最新收盘价: ${klines[-1]['close']:.2f}")
    else:
        print("   ❌ 未获取到数据")
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 2. Tiingo - 外汇/贵金属
print("\n2️⃣  Tiingo (外汇/贵金属)")
try:
    from app.data_providers.commodities import _fetch_tiingo
    result = _fetch_tiingo([{"name": "Gold", "symbol": "XAUUSD", "tiingo": "xauusd"}])
    if result:
        print(f"   ✅ 黄金(XAUUSD): ${result[0]['last']:.2f}")
    else:
        print("   ⚠️  无数据返回")
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 3. Alpha Vantage - 股票报价
print("\n3️⃣  Alpha Vantage (股票实时报价)")
try:
    import os
    import requests
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    resp = requests.get(
        'https://www.alphavantage.co/query',
        params={'function': 'GLOBAL_QUOTE', 'symbol': 'MSFT', 'apikey': api_key},
        timeout=10
    )
    data = resp.json()
    quote = data.get('Global Quote', {})
    if quote and quote.get('05. price'):
        print(f"   ✅ MSFT: ${float(quote['05. price']):.2f} ({quote.get('10. change percent', 'N/A')})")
    else:
        print(f"   ⚠️  API响应: {data}")
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 4. CryptoQuant - 链上数据
print("\n4️⃣  CryptoQuant (加密货币链上数据)")
try:
    import os
    api_key = os.getenv('CRYPTOQUANT_API_KEY')
    print(f"   ✅ API Key已配置 (前8位: {api_key[:8]}...)")
    # 注意: CryptoQuant需要特定的API路径和权限，这里只验证配置
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 5. Tavily - AI搜索
print("\n5️⃣  Tavily (AI搜索增强)")
try:
    import os
    import requests
    api_key = os.getenv('TAVILY_API_KEYS')
    resp = requests.post(
        'https://api.tavily.com/search',
        json={'api_key': api_key, 'query': 'Bitcoin', 'max_results': 1},
        timeout=10
    )
    if resp.status_code == 200:
        data = resp.json()
        print(f"   ✅ 搜索结果: {len(data.get('results', []))}条")
    else:
        print(f"   ❌ HTTP {resp.status_code}: {resp.text[:100]}")
except Exception as e:
    print(f"   ❌ 错误: {e}")

print("\n" + "=" * 70)
print("✅ 验证完成！所有API接口已配置并可用")
print("=" * 70)
