#!/usr/bin/env python3
import sys
sys.path.insert(0, '/app/backend_api_python')
from app.utils.db import get_db_connection

with get_db_connection() as db:
    cur = db.cursor()
    
    print("=" * 80)
    print("检查交易所凭证和API Key关联")
    print("=" * 80)
    
    # 查询凭证列表
    cur.execute('''
        SELECT ec.id, ec.name, ec.exchange_id, 
               ak.id as ak_id, ak.api_key, ak.key_name, ak.credential_id, ak.active
        FROM qd_exchange_credentials ec
        LEFT JOIN qd_api_keys ak ON ec.id = ak.credential_id
        ORDER BY ec.id DESC
        LIMIT 5
    ''')
    
    rows = cur.fetchall()
    
    print(f"\n找到 {len(rows)} 条记录：\n")
    for row in rows:
        print(f"凭证ID: {row['id']}")
        print(f"  名称: {row['name']}")
        print(f"  交易所: {row['exchange_id']}")
        print(f"  API Key ID: {row['ak_id']}")
        print(f"  API Key: {row['api_key'][:20] + '...' if row['api_key'] else 'None'}")
        print(f"  Key Name: {row['key_name']}")
        print(f"  Credential ID: {row['credential_id']}")
        print(f"  Active: {row['active']}")
        print("-" * 80)
    
    cur.close()
