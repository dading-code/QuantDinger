#!/usr/bin/env python3
"""生成完整测试数据 - 3个用户的自选、指标、策略、充值记录"""
import os
import sys
import json

if not os.getenv('DATABASE_URL'):
    with open('/app/.env', 'r') as f:
        for line in f:
            if line.startswith('DATABASE_URL='):
                os.environ['DATABASE_URL'] = line.strip().split('=', 1)[1]
                break

sys.path.insert(0, '/app')
from app.utils.db import get_db_connection

print("=" * 80)
print("QuantDinger 测试数据生成")
print("=" * 80)

with get_db_connection() as conn:
    cur = conn.cursor()
    
    # ===== 1. 检查现有用户 =====
    print("\n【1】检查现有用户...")
    cur.execute("SELECT id, username, email, credits FROM qd_users ORDER BY id LIMIT 10")
    users = cur.fetchall()
    
    if len(users) < 3:
        print(f"  ️ 只有 {len(users)} 个用户，建议先创建更多用户")
        if len(users) == 0:
            print("  ❌ 没有用户，无法继续")
            sys.exit(1)
    
    test_users = users[:3]
    print(f"  将为以下 {len(test_users)} 个用户生成数据:")
    for u in test_users:
        print(f"    ID={u['id']}, 用户名={u['username']}, 邮箱={u['email']}")
    
    user_ids = [u['id'] for u in test_users]
    
    # ===== 2. 检查交易所凭证 =====
    print("\n【2】检查交易所凭证...")
    cur.execute("SELECT id, name, exchange_id FROM qd_exchange_credentials WHERE user_id=1 ORDER BY id")
    credentials = cur.fetchall()
    default_credential_id = credentials[0]['id'] if credentials else None
    print(f"  找到 {len(credentials)} 个凭证")
    if default_credential_id:
        print(f"  使用凭证ID: {default_credential_id}")
    
    # ===== 3. 生成自选品种 =====
    print("\n【3】生成自选交易品种...")
    watchlist_items = [
        ('BTC/USDT', 'crypto', '比特币'),
        ('ETH/USDT', 'crypto', '以太坊'),
        ('BNB/USDT', 'crypto', '币安币'),
        ('SOL/USDT', 'crypto', 'Solana'),
        ('EUR/USD', 'forex', '欧元/美元'),
        ('GBP/USD', 'forex', '英镑/美元'),
        ('AAPL', 'stock', '苹果公司'),
        ('GOOGL', 'stock', '谷歌'),
    ]
    
    for user_id in user_ids:
        cur.execute("DELETE FROM qd_watchlist WHERE user_id = %s", (user_id,))
        for i, (symbol, market, name) in enumerate(watchlist_items):
            days_ago = i + 1
            cur.execute("""
                INSERT INTO qd_watchlist (user_id, market, symbol, name, created_at)
                VALUES (%s, %s, %s, %s, NOW() - (%s || ' days')::interval)
            """, (user_id, market, symbol, name, str(days_ago)))
        print(f"  ✓ 用户 {user_id}: 添加 {len(watchlist_items)} 个自选品种")
    
    conn.commit()
    
    # ===== 4. 生成指标代码 =====
    print("\n【4】生成指标代码...")
    indicator_codes = [
        ('RSI(14)', 'rsi', json.dumps({"period": 14, "overbought": 70, "oversold": 30})),
        ('MACD(12,26,9)', 'macd', json.dumps({"fast": 12, "slow": 26, "signal": 9})),
        ('EMA(20)', 'ema', json.dumps({"period": 20})),
        ('布林带(20,2)', 'bollinger', json.dumps({"period": 20, "std_dev": 2})),
        ('KDJ(9,3,3)', 'kdj', json.dumps({"period": 9, "k_period": 3, "d_period": 3})),
    ]
    
    for user_id in user_ids:
        cur.execute("DELETE FROM qd_indicator_codes WHERE user_id = %s", (user_id,))
        for name, code_name, config in indicator_codes:
            days_ago = indicator_codes.index((name, code_name, config)) + 1
            cur.execute("""
                INSERT INTO qd_indicator_codes (user_id, name, code, description, is_public, created_at)
                VALUES (%s, %s, %s, %s, TRUE, NOW() - (%s || ' days')::interval)
            """, (user_id, name, config, f"{name}指标", str(days_ago)))
        print(f"  ✓ 用户 {user_id}: 创建 {len(indicator_codes)} 个指标代码")
    
    conn.commit()
    
    # ===== 5. 生成交易策略 =====
    print("\n【5】生成交易策略...")
    strategies = [
        ('BTC趋势跟踪', 'ma_crossover', 'BTC/USDT', '1H', 10000, 1),
        ('ETH均值回归', 'rsi_oversold', 'ETH/USDT', '4H', 8000, 1),
        ('多币种组合策略', 'multi_asset', 'MULTI', '1D', 15000, 2),
        ('短线突破策略', 'bollinger_breakout', 'BTC/USDT', '15m', 5000, 3),
    ]
    
    for user_id in user_ids:
        cur.execute("DELETE FROM qd_strategies_trading WHERE user_id = %s", (user_id,))
        for i, (name, strategy_type, symbol, timeframe, capital, leverage) in enumerate(strategies):
            days_ago = i + 1
            cur.execute("""
                INSERT INTO qd_strategies_trading (
                    user_id, strategy_name, strategy_type, strategy_mode,
                    market_category, execution_mode, status, symbol, timeframe,
                    initial_capital, leverage, market_type, indicator_config,
                    trading_config, exchange_config, decide_interval, created_at, updated_at
                ) VALUES (%s, %s, %s, 'auto', 'Crypto', 'signal', 'stopped', %s, %s,
                         %s, %s, 'crypto', %s, %s, %s, %s, NOW() - (%s || ' days')::interval, NOW() - (%s || ' days')::interval)
            """, (
                user_id, name, strategy_type, symbol, timeframe,
                capital, leverage,
                json.dumps({"fast_period": 10, "slow_period": 30}),
                json.dumps({"initial_capital": capital, "leverage": leverage, "max_position_size": 0.2, "stop_loss": 0.05, "take_profit": 0.15}),
                str(default_credential_id) if default_credential_id else '1',
                60, str(days_ago), str(days_ago)
            ))
        print(f"  ✓ 用户 {user_id}: 创建 {len(strategies)} 个策略")
    
    conn.commit()
    
    # ===== 6. 生成充值记录 =====
    print("\n【6】生成充值记录...")
    recharge_types = [
        (1000, 'recharge', '支付宝充值'),
        (2000, 'recharge', '微信充值'),
        (5000, 'recharge', '银行转账'),
        (500, 'gift', '活动赠送'),
        (100, 'reward', '签到奖励'),
    ]
    
    for user_id in user_ids:
        cur.execute("DELETE FROM qd_credits_log WHERE user_id = %s", (user_id,))
        total_credits = sum(amount for amount, _, _ in recharge_types)
        
        # 更新用户积分
        cur.execute("UPDATE qd_users SET credits = %s WHERE id = %s", (total_credits, user_id))
        
        for i, (amount, action, remark) in enumerate(recharge_types):
            days_ago = len(recharge_types) - i
            cur.execute("""
                INSERT INTO qd_credits_log (
                    user_id, action, amount, balance_after, remark, created_at
                ) VALUES (%s, %s, %s, %s, %s, NOW() - (%s || ' days')::interval)
            """, (user_id, action, amount, total_credits, remark, str(days_ago)))
        
        print(f"  ✓ 用户 {user_id}: 充值 {len(recharge_types)} 次，总积分 {total_credits}")
    
    conn.commit()
    
    # ===== 7. 统计总览 =====
    print("\n" + "=" * 80)
    print("数据统计总览")
    print("=" * 80)
    
    stats = {
        '用户数': 'SELECT COUNT(*) as cnt FROM qd_users',
        '自选品种数': 'SELECT COUNT(*) as cnt FROM qd_watchlist',
        '指标代码数': 'SELECT COUNT(*) as cnt FROM qd_indicator_codes',
        '策略数': 'SELECT COUNT(*) as cnt FROM qd_strategies_trading',
        '充值记录数': 'SELECT COUNT(*) as cnt FROM qd_credits_log',
        'API Key数': 'SELECT COUNT(*) as cnt FROM qd_api_keys',
    }
    
    for name, sql in stats.items():
        cur.execute(sql)
        count = cur.fetchone()['cnt']
        print(f"  {name}: {count}")
    
    print("\n✅ 测试数据生成完成！")
