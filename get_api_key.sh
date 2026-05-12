#!/bin/bash
# Get first API key from database

podman exec backend python3 << 'EOF'
from app.utils.db import get_db_connection

db = get_db_connection()
cur = db.cursor()
cur.execute("SELECT api_key, key_name FROM qd_api_keys LIMIT 1")
row = cur.fetchone()

if row:
    print(f"API Key: {row['api_key']}")
    print(f"Key Name: {row['key_name']}")
else:
    print("No API keys found in database")

cur.close()
db.close()
EOF
