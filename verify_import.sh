#!/bin/bash
# 验证47.93.6.116数据库导入结果

echo "=========================================="
echo "检查表数量"
echo "=========================================="
PGPASSWORD="KGFhPRChLYJCy8bB" /www/server/pgsql/bin/psql -h 127.0.0.1 -U quantdinger -d quantdinger -c "SELECT count(*) as table_count FROM information_schema.tables WHERE table_schema = 'public';"

echo ""
echo "=========================================="
echo "列出所有表"
echo "=========================================="
PGPASSWORD="KGFhPRChLYJCy8bB" /www/server/pgsql/bin/psql -h 127.0.0.1 -U quantdinger -d quantdinger -c "\dt"

echo ""
echo "=========================================="
echo "检查用户数据"
echo "=========================================="
PGPASSWORD="KGFhPRChLYJCy8bB" /www/server/pgsql/bin/psql -h 127.0.0.1 -U quantdinger -d quantdinger -c "SELECT id, username, email FROM qd_users LIMIT 5;" 2>/dev/null || echo "No users table or data"
