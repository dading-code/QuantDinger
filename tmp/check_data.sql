-- 查询交易所凭证和API Key
\echo '=== 交易所凭证 ==='
SELECT id, COALESCE(name, '(空)') as name, exchange_id, COALESCE(api_key_hint, '(空)') as hint, created_at
FROM qd_exchange_credentials 
WHERE user_id=1 
ORDER BY id DESC 
LIMIT 5;

\echo ''
\echo '=== API密钥 ==='
SELECT id, COALESCE(key_name, '(空)') as key_name, 
       (api_key IS NOT NULL) as has_key, 
       credential_id, 
       active
FROM qd_api_keys 
WHERE user_id=1 
ORDER BY id DESC 
LIMIT 5;
