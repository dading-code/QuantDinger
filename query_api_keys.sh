#!/bin/bash
# Query real API keys from database
psql -h 47.93.6.116 -p 5432 -U quantdinger -d quantdinger -c "
SELECT k.id, k.key_name, substring(k.api_key_hash from 1 for 20) as hash_preview, k.credential_id, c.name as credential_name
FROM qd_api_keys k
LEFT JOIN qd_exchange_credentials c ON k.credential_id = c.id
ORDER BY k.id;
"
