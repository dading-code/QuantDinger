#!/usr/bin/env python3
"""Create a test trading strategy for the user"""
import os
import sys
import json

# Set DATABASE_URL from environment or .env file
if not os.getenv('DATABASE_URL'):
    try:
        with open('/app/.env', 'r') as f:
            for line in f:
                if line.startswith('DATABASE_URL='):
                    os.environ['DATABASE_URL'] = line.strip().split('=', 1)[1]
                    break
    except:
        pass

sys.path.insert(0, '/app')
from app.utils.db import get_db_connection

try:
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Step 1: Get user info (use first user)
        print("=" * 70)
        print("Creating Test Strategy")
        print("=" * 70)
        
        cur.execute("SELECT id, username, email FROM qd_users ORDER BY id ASC LIMIT 1")
        user = cur.fetchone()
        if not user:
            print("❌ No users found in database!")
            sys.exit(1)
        
        user_id = user["id"]
        username = user["username"]
        print(f"\n✓ Using user: {username} (ID: {user_id})")
        
        # Step 2: Check API keys
        cur.execute("""
            SELECT id, key_name, api_key, active 
            FROM qd_api_keys 
            WHERE user_id = %s AND active = TRUE
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,))
        api_key = cur.fetchone()
        
        if api_key:
            key_prefix = api_key['api_key'][:8] if api_key['api_key'] else 'unknown'
            print(f"✓ Found API key: {api_key['key_name']} ({key_prefix}...)")
        else:
            print("⚠️  No active API keys found. Creating strategy anyway...")
        
        # Step 3: Check exchange config (broker account)
        cur.execute("""
            SELECT id, exchange_id, name 
            FROM qd_exchange_credentials 
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,))
        exchange = cur.fetchone()
        
        broker_account_id = None
        if exchange:
            print(f"✓ Found exchange config: {exchange['exchange_id']} - {exchange['name']}")
            broker_account_id = str(exchange["id"])
        else:
            print("⚠️  No exchange config found. Will use default.")
        
        # Step 4: Create a simple MA Crossover strategy
        print("\n📝 Creating MA Crossover strategy...")
        
        strategy_config = {
            "fast_period": 10,
            "slow_period": 30,
            "timeframe": "1H"
        }
        
        trading_config = {
            "initial_capital": 10000,
            "leverage": 1,
            "risk_per_trade": 0.02,
            "max_positions": 1,
            "stop_loss_pct": 0.05,
            "take_profit_pct": 0.10
        }
        
        # Insert strategy
        cur.execute("""
            INSERT INTO qd_strategies_trading (
                user_id,
                strategy_name,
                strategy_type,
                strategy_mode,
                market_category,
                execution_mode,
                status,
                symbol,
                timeframe,
                initial_capital,
                leverage,
                market_type,
                indicator_config,
                trading_config,
                exchange_config,
                decide_interval,
                created_at,
                updated_at
            ) VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                NOW(),
                NOW()
            ) RETURNING id
        """, (
            user_id,
            "Test MA Crossover",
            "ma_crossover",
            "auto",
            "Crypto",
            "signal",  # Signal mode - push to local client
            "stopped",  # Start as stopped, user can start it manually
            "BTC/USDT",
            "1H",
            10000,
            1,
            "crypto",
            json.dumps(strategy_config),
            json.dumps(trading_config),
            broker_account_id,
            60  # Check every 60 minutes
        ))
        
        strategy_id = cur.fetchone()["id"]
        conn.commit()
        
        print(f"✅ Strategy created successfully!")
        print(f"\nStrategy Details:")
        print(f"  ID: {strategy_id}")
        print(f"  Name: Test MA Crossover")
        print(f"  Type: ma_crossover")
        print(f"  Symbol: BTC/USDT")
        print(f"  Timeframe: 1H")
        print(f"  Execution Mode: signal (pushes to local client)")
        print(f"  Status: stopped (ready to start)")
        print(f"\n💡 Next steps:")
        print(f"  1. Go to Web UI: http://39.105.150.99:8888")
        print(f"  2. Navigate to Strategies → Find 'Test MA Crossover'")
        print(f"  3. Click 'Start' button to begin trading")
        print(f"  4. Your local client will receive signals via WebSocket")
        
        cur.close()
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
