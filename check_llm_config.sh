#!/bin/bash
echo "检查LLM配置..."

docker exec -i quantdinger-db psql -U quantdinger -d quantdinger <<'EOSQL'
-- 检查系统配置表中的LLM设置
SELECT key, value FROM qd_system_config WHERE key LIKE '%llm%' OR key LIKE '%api%url%' OR key LIKE '%custom%';

-- 检查用户级别的LLM配置
SELECT user_id, config_key, LEFT(config_value, 50) as value_preview 
FROM qd_user_configs 
WHERE config_key LIKE '%llm%' OR config_key LIKE '%api%' 
LIMIT 10;
EOSQL
