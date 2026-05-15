#!/bin/bash
cd /opt/quantdinger/QuantDinger/backend_api_python
source .venv/bin/activate

python3 << 'EOF'
import psycopg2

conn = psycopg2.connect('postgresql://quantdinger:KGFhPRChLYJCy8bB@47.93.6.116:5432/quantdinger')
cur = conn.cursor()

# Check users
cur.execute('SELECT id, username, email FROM qd_users LIMIT 3')
users = cur.fetchall()
print("Users:")
for user in users:
    print(f"  ID: {user[0]}, Username: {user[1]}, Email: {user[2]}")

# Check API keys
cur.execute('SELECT id, user_id, key_name, active FROM qd_api_keys LIMIT 5')
keys = cur.fetchall()
print("\nAPI Keys:")
for key in keys:
    print(f"  ID: {key[0]}, User ID: {key[1]}, Name: {key[2]}, Active: {key[3]}")

cur.close()
conn.close()
EOF
