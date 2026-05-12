#!/usr/bin/env python3
"""
直接查询数据库验证API返回的数据
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
    print("模拟 list_credentials() API 查询")
    print("=" * 80)
    
    # 模拟后端接口的SQL查询（user_id=1）- 使用修复后的SQL
    cur.execute("""
        SELECT ec.id, ec.user_id, ec.name, ec.exchange_id, ec.api_key_hint, 
               ec.encrypted_config, ec.created_at, ec.updated_at,
               ak.api_key as api_key_value, ak.key_name as api_key_name
        FROM qd_exchange_credentials ec
        LEFT JOIN qd_api_keys ak ON ak.id = (
            SELECT id FROM qd_api_keys 
            WHERE credential_id = ec.id AND active = true 
            ORDER BY id DESC LIMIT 1
        )
        WHERE ec.user_id = %s
        ORDER BY ec.id DESC
    """, (1,))
    
    rows = cur.fetchall()
    
    print(f"\n找到 {len(rows)} 条凭证记录：\n")
    
    for row in rows:
        print(f"凭证ID: {row[0]}")
        print(f"  名称: {row[2]}")
        print(f"  交易所: {row[3]}")
        
        api_key_value = row[8]  # api_key_value
        
        if api_key_value:
            # 脱敏处理
            if len(api_key_value) > 12:
                masked_key = api_key_value[:8] + '...' + api_key_value[-4:]
            else:
                masked_key = api_key_value
            
            print(f"  ✅ API Key (脱敏): {masked_key}")
            print(f"  ✅ API Key (完整): {api_key_value[:20]}...")
            print(f"  ✅ Key Name: {row[9]}")
        else:
            print(f"  ❌ API Key: None (未设置)")
        
        print()
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
