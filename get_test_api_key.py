#!/usr/bin/env python3
"""Get a valid API key from database for testing."""

import sys
sys.path.insert(0, '/app')

from app.config.database import get_db_connection

try:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT api_key FROM user_api_keys LIMIT 1")
    row = cur.fetchone()
    
    if row:
        print(f"API_KEY={row[0]}")
    else:
        print("No API keys found in database")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
