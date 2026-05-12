#!/bin/bash
# 检查数据库API Key和凭证数据

echo "=== 数据库检查 ==="

# 在数据库容器中直接执行SQL
podman exec quantdinger-db psql -U quantdinger -d quantdinger <<'SQL'

\echo '=== 交易所凭证 ==='
SELECT id, user_id, COALESCE(name, '(空)') as name, exchange_id, COALESCE(api_key_hint, '(空)') as hint, created_at 
FROM qd_exchange_credentials 
WHERE user_id = 1 
ORDER BY id DESC 
LIMIT 5;

\echo ''
\echo '=== API密钥 ==='
SELECT id, user_id, COALESCE(key_name, '(空)') as key_name, 
       (api_key IS NOT NULL) as has_key, 
       credential_id, active 
FROM qd_api_keys 
WHERE user_id = 1 
ORDER BY id DESC 
LIMIT 5;

SQL
