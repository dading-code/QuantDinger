#!/bin/bash
echo "重置测试用户密码为 123456..."

# 使用Python生成正确的bcrypt哈希
HASH=$(docker exec -i quantdinger-backend python3 -c "
from werkzeug.security import generate_password_hash
print(generate_password_hash('123456'))
")

echo "生成的密码哈希: $HASH"

# 更新数据库
docker exec -i quantdinger-db psql -U quantdinger -d quantdinger <<EOSQL
UPDATE qd_users SET password_hash = '$HASH' WHERE username IN ('testuser', 'trader01');
EOSQL

echo ""
echo "验证更新结果:"
docker exec -i quantdinger-db psql -U quantdinger -d quantdinger <<'EOSQL'
SELECT id, username, LEFT(password_hash, 30) as hash_preview FROM qd_users WHERE username IN ('testuser', 'trader01', 'admin');
EOSQL

echo ""
echo "✅ 密码重置完成！现在可以使用密码 123456 登录 testuser 和 trader01"
