#!/usr/bin/env python3
"""
验证API Key关联修复结果
"""
import psycopg2

try:
    conn = psycopg2.connect(
        host='quantdinger-db',
        port='5432',
        database='quantdinger',
        user='quantdinger',
        password='quantdinger123'
    )
    cur = conn.cursor()
    
    print("=" * 80)
    print("验证API Key关联修复结果")
    print("=" * 80)
    
    # 查询凭证ID为1的所有API Key
    cur.execute("""
        SELECT ak.id, ak.credential_id, ak.key_name, ak.active, ak.created_at
        FROM qd_api_keys ak
        WHERE ak.credential_id = 1
        ORDER BY ak.id DESC
    """)
    
    rows = cur.fetchall()
    
    print(f"\n凭证ID=1的API Keys（共{len(rows)}个）：")
    for row in rows:
        print(f"  ID: {row[0]}, credential_id: {row[1]}, key_name: {row[2]}, active: {row[3]}, created: {row[4]}")
    
    # 查询最新的API Key详情
    cur.execute("""
        SELECT ec.id as cred_id, ec.name, ec.exchange_id, 
               ak.id as ak_id, ak.api_key, ak.key_name, ak.credential_id, ak.active 
        FROM qd_exchange_credentials ec 
        LEFT JOIN qd_api_keys ak ON ec.id = ak.credential_id AND ak.active = true
        WHERE ec.id = 1
        ORDER BY ak.id DESC
        LIMIT 1
    """)
    
    row = cur.fetchone()
    
    print(f"\n最新关联的API Key：")
    if row:
        print(f"  凭证ID: {row[0]}, 名称: {row[1]}, 交易所: {row[2]}")
        print(f"    -> API Key ID: {row[3]}")
        print(f"    -> api_key (前20位): {row[4][:20] if row[4] else 'None'}...")
        print(f"    -> key_name: {row[5]}")
        print(f"    -> credential_id: {row[6]}")
        print(f"    -> active: {row[7]}")
    else:
        print("  未找到关联的API Key")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
