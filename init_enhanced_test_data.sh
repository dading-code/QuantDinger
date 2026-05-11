#!/bin/bash
# ============================================================================
# QuantDinger 增强版测试数据初始化脚本
# ============================================================================
# 创建更多策略、指标、回测记录等测试数据
# ============================================================================

set -e

echo "========================================"
echo "QuantDinger 增强测试数据初始化"
echo "========================================"
echo ""

DB_CONTAINER="quantdinger-db"
DB_NAME="quantdinger"
DB_USER="quantdinger"

run_sql() {
    docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME <<EOF
$1
EOF
}

echo "[1/8] 检查数据库连接..."
if run_sql "SELECT 1;" > /dev/null 2>&1; then
    echo "✅ 数据库连接正常"
else
    echo "❌ 数据库连接失败"
    exit 1
fi
echo ""

echo "[2/8] 创建更多交易策略..."
run_sql "
INSERT INTO qd_strategies_trading (
    user_id, strategy_name, strategy_type, market_category, 
    symbol, timeframe, status, strategy_code, trading_config, created_at, updated_at
)
VALUES 
    -- testuser的策略
    (
        2,
        'RSI超买超卖策略',
        'IndicatorStrategy',
        'Crypto',
        'BTC/USDT',
        '4h',
        'stopped',
        '# @param rsi_period int 14 RSI周期\n# @param overbought int 70 超买线\n# @param oversold int 30 超卖线\n\nrsi = calculate_rsi(df[\"close\"], params.get(\"rsi_period\", 14))\noverbought = params.get(\"overbought\", 70)\noversold = params.get(\"oversold\", 30)\n\ndf[\"buy\"] = rsi < oversold\ndf[\"sell\"] = rsi > overbought',
        '{\"initial_capital\": 15000, \"leverage\": 1}',
        NOW() - INTERVAL '6 days',
        NOW() - INTERVAL '1 day'
    ),
    (
        2,
        'MACD趋势策略',
        'IndicatorStrategy',
        'Crypto',
        'ETH/USDT',
        '1D',
        'running',
        '# MACD指标策略\nmacd_line, signal_line, histogram = calculate_macd(df[\"close\"])\n\ndf[\"buy\"] = (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))\ndf[\"sell\"] = (macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1))',
        '{\"initial_capital\": 8000, \"leverage\": 2}',
        NOW() - INTERVAL '4 days',
        NOW()
    ),
    (
        2,
        '布林带突破策略',
        'ScriptStrategy',
        'Crypto',
        'BNB/USDT',
        '1h',
        'stopped',
        'def on_init(ctx):\n    ctx.param(\"bb_period\", 20)\n    ctx.param(\"bb_std\", 2.0)\n\ndef on_bar(ctx, bar):\n    upper, middle, lower = calculate_bollinger_bars(bar.close, ctx.param(\"bb_period\"), ctx.param(\"bb_std\"))\n    if bar.close > upper:\n        ctx.buy(price=bar.close, qty=0.5)\n    elif bar.close < lower:\n        ctx.sell(price=bar.close, qty=0.5)',
        '{\"initial_capital\": 12000, \"leverage\": 1}',
        NOW() - INTERVAL '3 days',
        NOW() - INTERVAL '12 hours'
    ),
    
    -- trader01的策略
    (
        3,
        '均线交叉策略-美股',
        'IndicatorStrategy',
        'USStock',
        'AAPL',
        '1D',
        'stopped',
        '# 双均线策略\nsma_20 = df[\"close\"].rolling(20).mean()\nsma_50 = df[\"close\"].rolling(50).mean()\n\ndf[\"buy\"] = (sma_20 > sma_50) & (sma_20.shift(1) <= sma_50.shift(1))\ndf[\"sell\"] = (sma_20 < sma_50) & (sma_20.shift(1) >= sma_50.shift(1))',
        '{\"initial_capital\": 50000, \"leverage\": 1}',
        NOW() - INTERVAL '8 days',
        NOW() - INTERVAL '2 days'
    ),
    (
        3,
        '动量突破策略',
        'ScriptStrategy',
        'USStock',
        'MSFT',
        '4h',
        'running',
        'def on_init(ctx):\n    ctx.param(\"momentum_period\", 10)\n    ctx.param(\"threshold\", 0.02)\n\ndef on_bar(ctx, bar):\n    momentum = (bar.close / bar.close[-ctx.param(\"momentum_period\")]) - 1\n    if momentum > ctx.param(\"threshold\"):\n        ctx.buy(price=bar.close, qty=10)\n    elif momentum < -ctx.param(\"threshold\"):\n        ctx.sell(price=bar.close, qty=10)',
        '{\"initial_capital\": 30000, \"leverage\": 1}',
        NOW() - INTERVAL '5 days',
        NOW()
    ),
    (
        3,
        '外汇均值回归',
        'IndicatorStrategy',
        'Forex',
        'EUR/USD',
        '1h',
        'stopped',
        '# 均值回归策略\nsma = df[\"close\"].rolling(50).mean()\nstd = df[\"close\"].rolling(50).std()\n\nupper_band = sma + 2 * std\nlower_band = sma - 2 * std\n\ndf[\"buy\"] = df[\"close\"] < lower_band\ndf[\"sell\"] = df[\"close\"] > upper_band',
        '{\"initial_capital\": 25000, \"leverage\": 10}',
        NOW() - INTERVAL '10 days',
        NOW() - INTERVAL '3 days'
    )
ON CONFLICT DO NOTHING;
" 2>/dev/null || true

echo "✅ 已创建6个新策略"
echo ""

echo "[3/8] 创建指标代码库..."
run_sql "
INSERT INTO qd_indicator_codes (
    user_id, name, description, code, category, is_public, status, created_at, updated_at
)
VALUES 
    (
        2,
        '自定义RSI指标',
        '相对强弱指数，用于判断超买超卖',
        'def calculate_custom_rsi(close, period=14):\n    delta = close.diff()\n    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()\n    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()\n    rs = gain / loss\n    rsi = 100 - (100 / (1 + rs))\n    return rsi',
        'Momentum',
        false,
        'approved',
        NOW() - INTERVAL '7 days',
        NOW() - INTERVAL '5 days'
    ),
    (
        2,
        '改进型MACD',
        '带有信号线的MACD指标',
        'def calculate_improved_macd(close, fast=12, slow=26, signal=9):\n    ema_fast = close.ewm(span=fast).mean()\n    ema_slow = close.ewm(span=slow).mean()\n    macd_line = ema_fast - ema_slow\n    signal_line = macd_line.ewm(span=signal).mean()\n    histogram = macd_line - signal_line\n    return macd_line, signal_line, histogram',
        'Trend',
        false,
        'approved',
        NOW() - INTERVAL '6 days',
        NOW() - INTERVAL '4 days'
    ),
    (
        2,
        '波动率指标ATR',
        '平均真实波幅，用于衡量市场波动性',
        'def calculate_atr(high, low, close, period=14):\n    tr1 = high - low\n    tr2 = abs(high - close.shift())\n    tr3 = abs(low - close.shift())\n    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)\n    atr = tr.rolling(window=period).mean()\n    return atr',
        'Volatility',
        false,
        'approved',
        NOW() - INTERVAL '5 days',
        NOW() - INTERVAL '3 days'
    ),
    (
        3,
        '成交量加权均线VWAP',
        '成交量加权平均价格',
        'def calculate_vwap(high, low, close, volume):\n    typical_price = (high + low + close) / 3\n    vwap = (typical_price * volume).cumsum() / volume.cumsum()\n    return vwap',
        'Volume',
        false,
        'pending',
        NOW() - INTERVAL '4 days',
        NOW() - INTERVAL '2 days'
    ),
    (
        3,
        '斐波那契回撤',
        '基于斐波那契数列的技术分析工具',
        'def calculate_fibonacci_retracement(high, low):\n    diff = high - low\n    levels = {\n        \"0.0\": high,\n        \"0.236\": high - 0.236 * diff,\n        \"0.382\": high - 0.382 * diff,\n        \"0.5\": high - 0.5 * diff,\n        \"0.618\": high - 0.618 * diff,\n        \"1.0\": low\n    }\n    return levels',
        'Pattern',
        false,
        'approved',
        NOW() - INTERVAL '3 days',
        NOW() - INTERVAL '1 day'
    )
ON CONFLICT DO NOTHING;
" 2>/dev/null || true

echo "✅ 已创建5个自定义指标"
echo ""

echo "[4/8] 创建更多回测记录..."
run_sql "
INSERT INTO qd_backtest_runs (
    user_id, strategy_id, market, symbol, timeframe,
    start_date, end_date, initial_capital, status,
    metrics_json, created_at, completed_at
)
SELECT 
    2,
    st.id,
    'Crypto',
    'BTC/USDT',
    '4h',
    '2024-02-01',
    '2024-04-30',
    15000,
    'completed',
    '{\"total_return_pct\": 18.7, \"sharpe_ratio\": 2.05, \"max_drawdown_pct\": -9.8, \"win_rate\": 65.2, \"total_trades\": 52, \"profit_factor\": 2.15, \"avg_win\": 285.5, \"avg_loss\": -132.8}',
    NOW() - INTERVAL '5 days',
    NOW() - INTERVAL '5 days' + INTERVAL '3 hours'
FROM qd_strategies_trading st
WHERE st.strategy_name = 'RSI超买超卖策略' AND st.user_id = 2
LIMIT 1
ON CONFLICT DO NOTHING;
" 2>/dev/null || true

run_sql "
INSERT INTO qd_backtest_runs (
    user_id, strategy_id, market, symbol, timeframe,
    start_date, end_date, initial_capital, status,
    metrics_json, created_at, completed_at
)
SELECT 
    2,
    st.id,
    'Crypto',
    'ETH/USDT',
    '1D',
    '2024-01-01',
    '2024-06-30',
    8000,
    'completed',
    '{\"total_return_pct\": 25.3, \"sharpe_ratio\": 1.92, \"max_drawdown_pct\": -11.5, \"win_rate\": 59.8, \"total_trades\": 38, \"profit_factor\": 1.98, \"avg_win\": 312.4, \"avg_loss\": -157.6}',
    NOW() - INTERVAL '3 days',
    NOW() - INTERVAL '3 days' + INTERVAL '2 hours'
FROM qd_strategies_trading st
WHERE st.strategy_name = 'MACD趋势策略' AND st.user_id = 2
LIMIT 1
ON CONFLICT DO NOTHING;
" 2>/dev/null || true

run_sql "
INSERT INTO qd_backtest_runs (
    user_id, strategy_id, market, symbol, timeframe,
    start_date, end_date, initial_capital, status,
    metrics_json, created_at, completed_at
)
SELECT 
    3,
    st.id,
    'USStock',
    'AAPL',
    '1D',
    '2023-06-01',
    '2024-06-01',
    50000,
    'completed',
    '{\"total_return_pct\": 32.5, \"sharpe_ratio\": 2.35, \"max_drawdown_pct\": -7.2, \"win_rate\": 68.5, \"total_trades\": 45, \"profit_factor\": 2.45, \"avg_win\": 825.3, \"avg_loss\": -336.9}',
    NOW() - INTERVAL '6 days',
    NOW() - INTERVAL '6 days' + INTERVAL '4 hours'
FROM qd_strategies_trading st
WHERE st.strategy_name = '均线交叉策略-美股' AND st.user_id = 3
LIMIT 1
ON CONFLICT DO NOTHING;
" 2>/dev/null || true

run_sql "
INSERT INTO qd_backtest_runs (
    user_id, strategy_id, market, symbol, timeframe,
    start_date, end_date, initial_capital, status,
    metrics_json, created_at, completed_at
)
SELECT 
    3,
    st.id,
    'Forex',
    'EUR/USD',
    '1h',
    '2024-03-01',
    '2024-09-01',
    25000,
    'completed',
    '{\"total_return_pct\": 12.8, \"sharpe_ratio\": 1.65, \"max_drawdown_pct\": -14.3, \"win_rate\": 55.2, \"total_trades\": 128, \"profit_factor\": 1.72, \"avg_win\": 145.6, \"avg_loss\": -84.7}',
    NOW() - INTERVAL '4 days',
    NOW() - INTERVAL '4 days' + INTERVAL '5 hours'
FROM qd_strategies_trading st
WHERE st.strategy_name = '外汇均值回归' AND st.user_id = 3
LIMIT 1
ON CONFLICT DO NOTHING;
" 2>/dev/null || true

echo "✅ 已创建4条回测记录"
echo ""

echo "[5/8] 创建策略交易记录..."
run_sql "
INSERT INTO qd_strategy_trades (
    user_id, strategy_id, symbol, type, price, amount, value, commission, profit, created_at
)
SELECT 
    2,
    st.id,
    'BTC/USDT',
    'open_long',
    42500.00,
    0.25,
    10625.00,
    10.63,
    NULL,
    NOW() - INTERVAL '2 days'
FROM qd_strategies_trading st
WHERE st.strategy_name = 'BTC双均线策略' AND st.user_id = 2
LIMIT 1
ON CONFLICT DO NOTHING;
" 2>/dev/null || true

run_sql "
INSERT INTO qd_strategy_trades (
    user_id, strategy_id, symbol, type, price, amount, value, commission, profit, created_at
)
SELECT 
    2,
    st.id,
    'BTC/USDT',
    'close_long',
    44200.00,
    0.25,
    11050.00,
    11.05,
    403.32,
    NOW() - INTERVAL '1 day'
FROM qd_strategies_trading st
WHERE st.strategy_name = 'BTC双均线策略' AND st.user_id = 2
LIMIT 1
ON CONFLICT DO NOTHING;
" 2>/dev/null || true

echo "✅ 已创建交易记录"
echo ""

echo "[6/8] 创建AI分析历史（更多样本）..."
run_sql "
INSERT INTO qd_analysis_memory (
    user_id, market, symbol, timeframe, language,
    analysis_type, summary, decision, confidence,
    created_at
)
VALUES 
    (2, 'Crypto', 'BTC/USDT', '1D', 'zh-CN', 'fast_analysis', '比特币在\$68,000附近形成支撑，成交量温和放大。技术指标显示短期反弹动能充足，但需警惕上方\$72,000阻力位。建议分批建仓。', 'BUY', 75, NOW() - INTERVAL '2 days'),
    (2, 'Crypto', 'ETH/USDT', '4h', 'zh-CN', 'fast_analysis', '以太坊跟随比特币走势，但相对强度较弱。等待突破\$3,600关键位后再考虑介入。当前观望为主。', 'HOLD', 62, NOW() - INTERVAL '1 day'),
    (2, 'Crypto', 'SOL/USDT', '1D', 'zh-CN', 'fast_analysis', 'Solana生态持续活跃，TVL增长明显。价格在\$150-160区间震荡，突破后可看高至\$180。逢低吸纳策略。', 'BUY', 72, NOW() - INTERVAL '18 hours'),
    (2, 'Crypto', 'BNB/USDT', '4h', 'zh-CN', 'fast_analysis', 'BNB受币安平台消息影响较大，近期横盘整理。建议等待明确方向选择后再操作。', 'HOLD', 58, NOW() - INTERVAL '12 hours'),
    (3, 'USStock', 'AAPL', '1D', 'en-US', 'fast_analysis', 'Apple showing strong technical setup after breaking above the 200-day MA. Volume confirmation suggests continuation. Target \$195.', 'BUY', 80, NOW() - INTERVAL '1 day'),
    (3, 'USStock', 'NVDA', '1D', 'en-US', 'fast_analysis', 'NVIDIA remains in strong uptrend driven by AI demand. However, valuation concerns warrant caution. Consider partial profit taking.', 'SELL', 68, NOW() - INTERVAL '8 hours'),
    (3, 'USStock', 'MSFT', '4h', 'en-US', 'fast_analysis', 'Microsoft consolidating near all-time highs. Cloud growth story intact. Accumulate on dips below \$420.', 'BUY', 76, NOW() - INTERVAL '5 hours'),
    (3, 'Forex', 'EUR/USD', '1D', 'en-US', 'fast_analysis', 'EUR/USD facing resistance at 1.0950. ECB policy divergence with Fed creating headwinds. Bearish bias prevails.', 'SELL', 71, NOW() - INTERVAL '3 hours')
ON CONFLICT DO NOTHING;
" 2>/dev/null || true

echo "✅ 已创建8条AI分析记录"
echo ""

echo "[7/8] 添加更多自选币种..."
run_sql "
INSERT INTO qd_watchlist (user_id, market, symbol, name, created_at, updated_at)
VALUES 
    -- testuser的更多币种
    (2, 'Crypto', 'ADA/USDT', 'Cardano', NOW() - INTERVAL '3 days', NOW()),
    (2, 'Crypto', 'DOT/USDT', 'Polkadot', NOW() - INTERVAL '3 days', NOW()),
    (2, 'Crypto', 'MATIC/USDT', 'Polygon', NOW() - INTERVAL '2 days', NOW()),
    (2, 'Crypto', 'AVAX/USDT', 'Avalanche', NOW() - INTERVAL '2 days', NOW()),
    (2, 'USStock', 'GOOGL', 'Alphabet Inc.', NOW() - INTERVAL '1 day', NOW()),
    (2, 'USStock', 'AMZN', 'Amazon.com Inc.', NOW() - INTERVAL '1 day', NOW()),
    -- trader01的更多币种
    (3, 'USStock', 'TSLA', 'Tesla Inc.', NOW() - INTERVAL '2 days', NOW()),
    (3, 'USStock', 'META', 'Meta Platforms', NOW() - INTERVAL '2 days', NOW()),
    (3, 'Forex', 'GBP/USD', 'British Pound', NOW() - INTERVAL '1 day', NOW()),
    (3, 'Forex', 'USD/JPY', 'Japanese Yen', NOW() - INTERVAL '1 day', NOW())
ON CONFLICT (user_id, market, symbol) DO NOTHING;
" 2>/dev/null || true

echo "✅ 已添加10个自选币种"
echo ""

echo "[8/8] 更新用户积分..."
run_sql "
UPDATE qd_users SET credits = credits + 500 WHERE id = 2;
UPDATE qd_users SET credits = credits + 300 WHERE id = 3;
" 2>/dev/null || true

echo "✅ 积分已更新"
echo ""

echo "========================================"
echo "✅ 增强测试数据初始化完成！"
echo "========================================"
echo ""
echo "新增数据统计："
echo "  • 6个新交易策略（共9个）"
echo "  • 5个自定义指标"
echo "  • 4条回测记录（共6条）"
echo "  • 8条AI分析历史（共21条）"
echo "  • 10个新自选币种（共20个）"
echo "  • 2条策略交易记录"
echo "  • 用户积分增加（testuser: +500, trader01: +300）"
echo ""
echo "登录信息："
echo "  用户名: testuser 或 trader01"
echo "  密码: 123456"
echo ""
echo "访问地址: http://39.105.150.99:8888"
echo ""
