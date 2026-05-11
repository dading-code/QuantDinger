#!/bin/bash
echo "=========================================="
echo "QuantDinger 测试数据快速验证"
echo "=========================================="
echo ""

docker exec -i quantdinger-db psql -U quantdinger -d quantdinger <<'EOSQL'

-- 用户列表
\echo '【用户账户】'
SELECT id, username, credits FROM qd_users WHERE username IN ('testuser', 'trader01');

-- 策略列表
\echo ''
\echo '【交易策略】'
SELECT id, strategy_name, symbol, status FROM qd_strategies_trading WHERE user_id IN (2, 3);

-- AI分析历史（最新5条）
\echo ''
\echo '【AI分析历史（最新5条）】'
SELECT id, market, symbol, decision, confidence FROM qd_analysis_memory ORDER BY id DESC LIMIT 5;

-- 自选列表
\echo ''
\echo '【自选列表】'
SELECT id, name FROM qd_watchlist WHERE user_id IN (2, 3);

-- 统计数据
\echo ''
\echo '【数据统计】'
SELECT '用户数' as item, COUNT(*)::text as count FROM qd_users WHERE username IN ('testuser', 'trader01')
UNION ALL
SELECT '策略数', COUNT(*)::text FROM qd_strategies_trading WHERE user_id IN (2, 3)
UNION ALL
SELECT 'AI分析数', COUNT(*)::text FROM qd_analysis_memory
UNION ALL
SELECT '自选列表数', COUNT(*)::text FROM qd_watchlist WHERE user_id IN (2, 3);

EOSQL

echo ""
echo "=========================================="
echo "✅ 验证完成"
echo "=========================================="
echo ""
echo "访问地址: http://39.105.150.99:8888"
echo "登录账号: testuser / 123456"
echo ""
