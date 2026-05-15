#!/bin/bash
# 重启47.93.6.116的PostgreSQL并配置远程访问

echo "=========================================="
echo "1. 检查listen_addresses配置"
echo "=========================================="
grep listen_addresses /www/server/pgsql/data/postgresql.conf | head -1

echo ""
echo "2. 启动PostgreSQL（以postgres用户）"
echo "=========================================="
su - postgres -c "/www/server/pgsql/bin/pg_ctl start -D /www/server/pgsql/data -l /www/server/pgsql/data/logfile"

echo ""
echo "3. 等待3秒..."
sleep 3

echo ""
echo "4. 检查PostgreSQL状态"
echo "=========================================="
netstat -tlnp | grep 5432

echo ""
echo "5. 测试本地连接"
echo "=========================================="
PGPASSWORD="KGFhPRChLYJCy8bB" /www/server/pgsql/bin/psql -h 127.0.0.1 -U quantdinger -d quantdinger -c "SELECT 'Local connection OK' as status;"
