#!/bin/bash
# 配置47.93.6.116的PostgreSQL允许远程连接

echo "=========================================="
echo "1. 修改listen_addresses"
echo "=========================================="
sed -i "s/^#listen_addresses = 'localhost'/listen_addresses = '*'/" /www/server/pgsql/data/postgresql.conf
grep listen_addresses /www/server/pgsql/data/postgresql.conf | head -3

echo ""
echo "=========================================="
echo "2. 重启PostgreSQL服务"
echo "=========================================="
/www/server/pgsql/bin/pg_ctl restart -D /www/server/pgsql/data

echo ""
echo "=========================================="
echo "3. 检查PostgreSQL状态"
echo "=========================================="
/www/server/pgsql/bin/pg_ctl status -D /www/server/pgsql/data

echo ""
echo "=========================================="
echo "4. 测试远程连接（从本地）"
echo "=========================================="
sleep 3
PGPASSWORD="KGFhPRChLYJCy8bB" /www/server/pgsql/bin/psql -h 47.93.6.116 -U quantdinger -d quantdinger -c "SELECT version();"
