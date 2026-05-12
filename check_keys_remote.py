#!/usr/bin/env python3
"""
在容器内检查API Key与凭证的关联情况
"""
import sys
sys.path.insert(0, '/app/backend_api_python')

from app.utils.db import get_db_connection

with get_db_connection() as db:
    cur = db.cursor()
    
    print("=" * 80)
    print("检查API Key与凭证关联情况")
    print("=" * 80)
    
    # 1. 检查所有API Key
    cur.execute("SELECT id, credential_id, key_name, active FROM qd_api_keys ORDER BY id DESC LIMIT 10")
    api_keys = cur.fetchall()
    
    print("\n1. 最近的API Key：")
    for ak in api_keys:
        print(f"  ID: {ak['id']}, credential_id: {ak['credential_id']}, key_name: {ak['key_name']}, active: {ak['active']}")
    
    # 2. 检查所有凭证
    cur.execute("SELECT id, name, exchange_id FROM qd_exchange_credentials ORDER BY id DESC LIMIT 10")
    credentials = cur.fetchall()
    
    print("\n2. 最近的凭证：")
    for cred in credentials:
        print(f"  ID: {cred['id']}, name: {cred['name']}, exchange: {cred['exchange_id']}")
    
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
    for row in rows:
        print(f"  凭证ID: {row['cred_id']}, 名称: {row['name']}, 交易所: {row['exchange_id']}")
        print(f"    -> API Key ID: {row['ak_id']}, key_name: {row['key_name']}, credential_id: {row['credential_id']}, active: {row['active']}")
    
    cur.close()
