#!/bin/bash
# 检查API Key是否关联了credential_id

ssh root@39.105.150.99 'podman exec backend python3 -c "
import os, psycopg2
conn = psycopg2.connect(
    host=os.getenv('\''DB_HOST'\'', '\''db'\''),
    port=os.getenv('\''DB_PORT'\'', '\''5432'\''),
    database=os.getenv('\''DB_NAME'\'', '\''quantdinger'\''),
    user=os.getenv('\''DB_USER'\'', '\''postgres'\''),
    password=os.getenv('\''DB_PASSWORD'\'', '\''quantdinger123'\'')
)
cur = conn.cursor()
cur.execute('\''SELECT id, credential_id, key_name, active FROM qd_api_keys ORDER BY id DESC LIMIT 5'\'')
rows = cur.fetchall()
print('\''API Keys表（最近5条）:'\'')
for r in rows:
    print(f'\''  ID: {r[0]}, credential_id: {r[1]}, key_name: {r[2]}, active: {r[3]}'\'')
print()
cur.execute('\''SELECT id, name, exchange_id FROM qd_exchange_credentials ORDER BY id DESC LIMIT 5'\'')
rows = cur.fetchall()
print('\''交易所凭证表（最近5条）:'\'')
for r in rows:
    print(f'\''  ID: {r[0]}, name: {r[1]}, exchange: {r[2]}'\'')
cur.close()
conn.close()
"'
