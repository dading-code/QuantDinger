-- 修复交易所凭证的name字段
UPDATE qd_exchange_credentials 
SET name = 'DooTechnology-Demo' 
WHERE id = 1 AND (name IS NULL OR name = '');

-- 验证更新
SELECT id, COALESCE(name, '(空)') as name, exchange_id, api_key_hint 
FROM qd_exchange_credentials 
WHERE id = 1;
