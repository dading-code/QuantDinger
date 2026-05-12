#!/bin/bash
echo "=== 交易所凭证 ==="
podman exec quantdinger-db psql -U quantdinger -d quantdinger -t -A -F" | " -c "
SELECT id, COALESCE(name, '(空)'), exchange_id, COALESCE(api_key_hint, '(空)'), created_at
FROM qd_exchange_credentials 
WHERE user_id=1 
ORDER BY id DESC 
LIMIT 5;
"

echo ""
echo "=== API密钥 ==="
podman exec quantdinger-db psql -U quantdinger -d quantdinger -t -A -F" | " -c "
SELECT id, COALESCE(key_name, '(空)'), (api_key IS NOT NULL) as has_key, credential_id, active
FROM qd_api_keys 
WHERE user_id=1 
ORDER BY id DESC 
LIMIT 5;
"
