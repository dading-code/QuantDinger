#!/usr/bin/env python3
"""
修复API Key的credential_id关联
"""
import psycopg2

try:
    conn = psycopg2.connect(
        host='quantdinger-db',
        port='5432',
        database='quantdinger',
        user='quantdinger',  # 正确的用户名
        password='quantdinger123'  # 使用正确的密码
    )
    cur = conn.cursor()
    
    print("=" * 80)
    print("修复API Key的credential_id关联")
    print("=" * 80)
    
    # 更新API Key的credential_id
    cur.execute("""
        UPDATE qd_api_keys 
        SET credential_id = 1 
        WHERE id = 12 AND credential_id IS NULL
    """)
    
    conn.commit()
    print(f"\n✅ 已更新 {cur.rowcount} 条记录")
    
    # 验证更新结果
    cur.execute("SELECT id, credential_id, key_name, active FROM qd_api_keys WHERE id = 12")
    row = cur.fetchone()
    
    print(f"\n更新后的API Key：")
    print(f"  ID: {row[0]}, credential_id: {row[1]}, key_name: {row[2]}, active: {row[3]}")
    
    # 关联查询验证
    cur.execute("""
        SELECT ec.id as cred_id, ec.name, ec.exchange_id, 
               ak.id as ak_id, ak.key_name, ak.credential_id, ak.active 
        FROM qd_exchange_credentials ec 
        LEFT JOIN qd_api_keys ak ON ec.id = ak.credential_id 
        WHERE ec.id = 1
    """)
    
    row = cur.fetchone()
    
    print(f"\n关联查询结果：")
    print(f"  凭证ID: {row[0]}, 名称: {row[1]}, 交易所: {row[2]}")
    print(f"    -> API Key ID: {row[3]}, key_name: {row[4]}, credential_id: {row[5]}, active: {row[6]}")
    
    cur.close()
    conn.close()
    
    print("\n✅ 修复完成！请刷新前端页面查看效果。")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
