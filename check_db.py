import psycopg2
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:quantdinger123@localhost:5432/quantdinger')

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT ec.id as cred_id, ec.name, ec.exchange_id, 
               ak.id as ak_id, ak.api_key, ak.key_name, ak.credential_id, ak.active 
        FROM qd_exchange_credentials ec 
        LEFT JOIN qd_api_keys ak ON ec.id = ak.credential_id 
        ORDER BY ec.id DESC LIMIT 5;
    """)
    
    rows = cur.fetchall()
    
    print("=" * 80)
    print("交易所凭证和API Key关联查询结果")
    print("=" * 80)
    
    if not rows:
        print("\n没有找到任何记录")
    else:
        for row in rows:
            print(f"\n凭证ID: {row[0]}")
            print(f"  名称: {row[1]}")
            print(f"  交易所: {row[2]}")
            print(f"  API Key ID: {row[3]}")
            print(f"  API Key: {row[4][:20] + '...' if row[4] else 'None'}")
            print(f"  Key Name: {row[5]}")
            print(f"  Credential ID: {row[6]}")
            print(f"  Active: {row[7]}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
