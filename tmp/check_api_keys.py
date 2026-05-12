#!/usr/bin/env python3
"""检查API Key和交易所凭证数据"""
import os
import sys

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

print("=" * 80)
print("API Key 和交易所凭证数据检查")
print("=" * 80)

with get_db_connection() as conn:
    cur = conn.cursor()
    
    # 1. 检查API Keys
    print("\n[1] qd_api_keys 表（API密钥）:")
    cur.execute("""
        SELECT id, user_id, key_name, api_key, credential_id, active, created_at
        FROM qd_api_keys
        ORDER BY id DESC
        LIMIT 10
    """)
    api_keys = cur.fetchall()
    
    if api_keys:
        print(f"  找到 {len(api_keys)} 条记录:")
        for key in api_keys:
            key_preview = key['api_key'][:20] + '...' if key['api_key'] else 'NULL'
            print(f"  ID={key['id']}, User={key['user_id']}, Name='{key['key_name']}', "
                  f"Key={key_preview}, Credential={key['credential_id']}, Active={key['active']}")
    else:
        print("  ️ 没有找到任何API Key记录！")
    
    # 2. 检查交易所凭证
    print("\n[2] qd_exchange_credentials 表（交易所凭证）:")
    cur.execute("""
        SELECT id, user_id, name, exchange_id, api_key_hint, created_at
        FROM qd_exchange_credentials
        ORDER BY id DESC
        LIMIT 10
    """)
    credentials = cur.fetchall()
    
    if credentials:
        print(f"  找到 {len(credentials)} 条记录:")
        for cred in credentials:
            print(f"  ID={cred['id']}, User={cred['user_id']}, Name='{cred['name']}', "
                  f"Exchange={cred['exchange_id']}, Hint='{cred['api_key_hint']}'")
    else:
        print("  ⚠️ 没有找到任何交易所凭证记录！")
    
    # 3. 检查绑定关系
    print("\n[3] API Key 与交易所凭证的绑定关系:")
    cur.execute("""
        SELECT 
            ak.id as api_key_id,
            ak.key_name,
            ak.api_key,
            ak.credential_id,
            ec.id as cred_id,
            ec.name as cred_name,
            ec.exchange_id
        FROM qd_api_keys ak
        LEFT JOIN qd_exchange_credentials ec ON ak.credential_id = ec.id
        WHERE ak.user_id = 1
        ORDER BY ak.id DESC
    """)
    bindings = cur.fetchall()
    
    if bindings:
        print(f"  找到 {len(bindings)} 条绑定记录:")
        for b in bindings:
            key_preview = b['api_key'][:20] + '...' if b['api_key'] else 'NULL'
            cred_info = f"{b['cred_name']} ({b['exchange_id']})" if b['cred_id'] else '未绑定'
            print(f"  API Key ID={b['api_key_id']}, Name='{b['key_name']}', "
                  f"Key={key_preview}")
            print(f"    → Bound to: {cred_info}")
    else:
        print("  ⚠️ 没有找到任何绑定记录！")
    
    cur.close()

print("\n" + "=" * 80)
print("诊断建议:")
print("=" * 80)
print("如果API Key为NULL或不存在，需要:")
print("  1. 在Web后台创建API Key")
print("  2. 确保API Key绑定到正确的交易所凭证")
print("  3. API Key必须 active=TRUE")
print("=" * 80)
