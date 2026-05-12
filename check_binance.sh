#!/bin/bash
# 检查Binance连接状态

echo "检查CCXT和Binance连接..."
podman exec backend python3 << 'EOF'
import ccxt
print(f"CCXT版本: {ccxt.__version__}")

try:
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'timeout': 5000
    })
    
    # 尝试获取交易所信息
    markets = exchange.load_markets()
    print(f"✅ Binance连接成功")
    print(f"   可用交易对数量: {len(markets)}")
    
    # 检查BTC/USDT
    if 'BTC/USDT' in markets:
        print(f"   ✅ BTC/USDT 可用")
    else:
        print(f"   ❌ BTC/USDT 不可用")
        
except Exception as e:
    print(f"❌ Binance连接失败: {type(e).__name__}: {str(e)[:100]}")
    print(f"   可能原因: 网络限制、防火墙、或Binance API不可达")
EOF
