#!/bin/bash
# 查询 qd_api_keys 表
podman exec backend python -c "
from app.utils.db import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
cur.execute('''
    SELECT k.id, k.key_name, k.api_key_hash, k.credential_id, c.name as credential_name
    FROM qd_api_keys k
    LEFT JOIN qd_exchange_credentials c ON k.credential_id = c.id
    ORDER BY k.id
''')
rows = cur.fetchall()
for r in rows:
    print(f\"ID={r['id']} | Name={r['key_name']} | Hash={str(r['api_key_hash'])[:20]}... | CredID={r['credential_id']} | CredName={r['credential_name']}\")
cur.close()
conn.close()
"
