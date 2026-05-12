#!/usr/bin/env python3
"""
检查数据库中API Key与凭证的关联情况
"""
import psycopg2

try:
    # 数据库容器名是 quantdinger-db
    conn = psycopg2.connect(
        host='quantdinger-db',  # 使用容器名
        port='5432',
        database='quantdinger',
        user='postgres',
        password='quantdinger123'
    )
    cur = conn.cursor()
    
    print("=" * 80)
    print("检查API Key与凭证关联情况")
    print("=" * 80)
    
    # 1. 检查所有API Key
    cur.execute("SELECT id, credential_id, key_name, active FROM qd_api_keys ORDER BY id DESC LIMIT 10")
    api_keys = cur.fetchall()
    
    print("\n1. API Keys表（最近10条）：")
    if not api_keys:
        print("  (空)")
    else:
        for ak in api_keys:
            print(f"  ID: {ak[0]}, credential_id: {ak[1]}, key_name: {ak[2]}, active: {ak[3]}")
    
    # 2. 检查所有凭证
    cur.execute("SELECT id, name, exchange_id FROM qd_exchange_credentials ORDER BY id DESC LIMIT 10")
    credentials = cur.fetchall()
    
    print("\n2. 交易所凭证表（最近10条）：")
    if not credentials:
        print("  (空)")
    else:
        for cred in credentials:
            print(f"  ID: {cred[0]}, name: {cred[1]}, exchange: {cred[2]}")
    
    # 3. 关联查询
    cur.execute("""
        SELECT ec.id as cred_id, ec.name, ec.exchange_id, 
               ak.id as ak_id, ak.key_name, ak.credential_id, ak.active 
        FROM qd_exchange_credentials ec 
        LEFT JOIN qd_api_keys ak ON ec.id = ak.credential_id 
        ORDER BY ec.id DESC LIMIT 10
    """)
    
    rows = cur.fetchall()
    
    print("\n3. 关联查询结果（凭证 LEFT JOIN API Key）：")
    if not rows:
        print("  (空)")
    else:
        for row in rows:
            print(f"  凭证ID: {row[0]}, 名称: {row[1]}, 交易所: {row[2]}")
            if row[3]:  # 有API Key
                print(f"    -> API Key ID: {row[3]}, key_name: {row[4]}, credential_id: {row[5]}, active: {row[6]}")
            else:  # 没有API Key
                print(f"    -> 无API Key")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
