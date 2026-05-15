#!/usr/bin/env python3
import psycopg2

try:
    conn = psycopg2.connect(
        host='47.93.6.116',
        port=5432,
        database='quantdinger',
        user='quantdinger',
        password='KGFhPRChLYJCy8bB'
    )
    cur = conn.cursor()
    cur.execute("SELECT version();")
    print("✅ 连接成功！")
    print(f"PostgreSQL版本: {cur.fetchone()[0]}")
    
    # 检查表数量
    cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")
    table_count = cur.fetchone()[0]
    print(f"表数量: {table_count}")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"❌ 连接失败: {e}")
