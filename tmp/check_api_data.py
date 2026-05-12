#!/usr/bin/env python3
import os
import sys

if not os.getenv('DATABASE_URL'):
    with open('/app/.env', 'r') as f:
        for line in f:
            if line.startswith('DATABASE_URL='):
                os.environ['DATABASE_URL'] = line.strip().split('=', 1)[1]
                break

sys.path.insert(0, '/app')
from app.utils.db import get_db_connection

print("=" * 70)
print("API Key 和交易所凭证数据检查")
print("=" * 70)

with get_db_connection() as conn:
    cur = conn.cursor()
    
    # 检查API Keys
    print("\n[1] qd_api_keys 表（API密钥）:")
    cur.execute("""
        SELECT id, user_id, key_name, 
               CASE WHEN api_key IS NOT NULL THEN 'YES' ELSE 'NO' END as has_key,
               credential_id, active, created_at
        FROM qd_api_keys 
        WHERE user_id = 1
        ORDER BY id DESC
        LIMIT 10
    """)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"  ID={r['id']}, Name={r['key_name']}, HasKey={r['has_key']}, "
                  f"CredID={r['credential_id']}, Active={r['active']}")
    else:
        print("  ⚠️ 没有找到任何API Key！")
    
    # 检查交易所凭证
    print("\n[2] qd_exchange_credentials 表（交易所凭证）:")
    cur.execute("""
        SELECT id, user_id, name, exchange_id, api_key_hint, created_at
        FROM qd_exchange_credentials 
        WHERE user_id = 1
        ORDER BY id DESC
        LIMIT 10
    """)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"  ID={r['id']}, Name={r['name']}, Exchange={r['exchange_id']}, "
                  f"Hint={r['api_key_hint']}")
    else:
        print("  ⚠️ 没有找到任何交易所凭证！")
    
    # 检查绑定关系
    print("\n[3] 绑定关系:")
    cur.execute("""
        SELECT ak.id, ak.key_name, ak.credential_id, 
               ec.name as cred_name, ec.exchange_id
        FROM qd_api_keys ak
        LEFT JOIN qd_exchange_credentials ec ON ak.credential_id = ec.id
        WHERE ak.user_id = 1
        ORDER BY ak.id DESC
    """)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            cred_info = f"{r['cred_name']} ({r['exchange_id']})" if r['cred_name'] else "未绑定"
            print(f"  API Key ID={r['id']} ({r['key_name']}) -> {cred_info}")
    else:
        print("  ⚠️ 没有找到绑定关系！")
    
    cur.close()

print("\n" + "=" * 70)
