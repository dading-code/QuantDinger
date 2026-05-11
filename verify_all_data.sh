#!/bin/bash
echo "=========================================="
echo "QuantDinger 完整测试数据验证"
echo "=========================================="
echo ""

DB_CONTAINER="quantdinger-db"
DB_NAME="quantdinger"
DB_USER="quantdinger"

docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME <<'EOSQL'

-- 用户统计
\echo '【用户账户】'
SELECT id, username, credits FROM qd_users WHERE username IN ('testuser', 'trader01');

-- 策略列表
\echo ''
\echo '【交易策略（按用户分组）】'
SELECT 
    u.username,
    st.strategy_name,
    st.market_category,
    st.symbol,
    st.timeframe,
    st.status,
    st.strategy_type
FROM qd_strategies_trading st
JOIN qd_users u ON st.user_id = u.id
WHERE u.username IN ('testuser', 'trader01')
ORDER BY u.username, st.created_at DESC;

-- 指标代码库
\echo ''
\echo '【自定义指标】'
SELECT 
    u.username,
    ic.name,
    ic.category,
    ic.status
FROM qd_indicator_codes ic
JOIN qd_users u ON ic.user_id = u.id
WHERE u.username IN ('testuser', 'trader01')
ORDER BY u.username;

-- 回测记录
\echo ''
\echo '【回测记录】'
SELECT 
    u.username,
    br.market,
    br.symbol,
    br.timeframe,
    br.status,
    (br.metrics_json->>'total_return_pct')::numeric(5,2) as return_pct,
    (br.metrics_json->>'sharpe_ratio')::numeric(4,2) as sharpe
FROM qd_backtest_runs br
JOIN qd_users u ON br.user_id = u.id
WHERE u.username IN ('testuser', 'trader01')
ORDER BY u.username, br.created_at DESC;

-- AI分析历史（最近10条）
\echo ''
\echo '【AI分析历史（最近10条）】'
SELECT 
    u.username,
    am.market,
    am.symbol,
    am.decision,
    am.confidence,
    am.created_at::date as analysis_date
FROM qd_analysis_memory am
JOIN qd_users u ON am.user_id = u.id
WHERE u.username IN ('testuser', 'trader01')
ORDER BY am.created_at DESC
LIMIT 10;

-- 自选列表统计
\echo ''
\echo '【自选币种统计】'
SELECT 
    u.username,
    w.market,
    COUNT(*) as symbol_count,
    STRING_AGG(w.symbol, ', ' ORDER BY w.symbol) as symbols
FROM qd_watchlist w
JOIN qd_users u ON w.user_id = u.id
WHERE u.username IN ('testuser', 'trader01')
GROUP BY u.username, w.market
ORDER BY u.username, w.market;

-- 策略交易记录
\echo ''
\echo '【策略交易记录】'
SELECT 
    u.username,
    st.symbol,
    st.type,
    st.price,
    st.amount,
    st.profit,
    st.created_at::timestamp(0) as trade_time
FROM qd_strategy_trades st
JOIN qd_users u ON st.user_id = u.id
WHERE u.username IN ('testuser', 'trader01')
ORDER BY st.created_at DESC;

-- 总体统计
\echo ''
\echo '【总体数据统计】'
SELECT '用户数' as category, COUNT(*)::text as count FROM qd_users WHERE username IN ('testuser', 'trader01')
UNION ALL
SELECT '策略总数', COUNT(*)::text FROM qd_strategies_trading st JOIN qd_users u ON st.user_id = u.id WHERE u.username IN ('testuser', 'trader01')
UNION ALL
SELECT '运行中策略', COUNT(*)::text FROM qd_strategies_trading st JOIN qd_users u ON st.user_id = u.id WHERE u.username IN ('testuser', 'trader01') AND st.status = 'running'
UNION ALL
SELECT '自定义指标', COUNT(*)::text FROM qd_indicator_codes ic JOIN qd_users u ON ic.user_id = u.id WHERE u.username IN ('testuser', 'trader01')
UNION ALL
SELECT '回测记录', COUNT(*)::text FROM qd_backtest_runs br JOIN qd_users u ON br.user_id = u.id WHERE u.username IN ('testuser', 'trader01')
UNION ALL
SELECT 'AI分析记录', COUNT(*)::text FROM qd_analysis_memory am JOIN qd_users u ON am.user_id = u.id WHERE u.username IN ('testuser', 'trader01')
UNION ALL
SELECT '自选币种', COUNT(*)::text FROM qd_watchlist w JOIN qd_users u ON w.user_id = u.id WHERE u.username IN ('testuser', 'trader01')
UNION ALL
SELECT '交易记录', COUNT(*)::text FROM qd_strategy_trades st JOIN qd_users u ON st.user_id = u.id WHERE u.username IN ('testuser', 'trader01');

EOSQL

echo ""
echo "=========================================="
echo "✅ 验证完成"
echo "=========================================="
echo ""
echo "访问地址: http://39.105.150.99:8888"
echo "登录账号: testuser / 123456"
echo ""
