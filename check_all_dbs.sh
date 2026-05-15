#!/bin/bash
# 检查47.93.6.116上的所有数据库

echo "=========================================="
echo "列出所有数据库"
echo "=========================================="
/www/server/pgsql/bin/psql -U quantdinger -c "\l"

echo ""
echo "=========================================="
echo "检查当前数据库的所有schema"
echo "=========================================="
/www/server/pgsql/bin/psql -U quantdinger -d quantdinger -c "SELECT schema_name FROM information_schema.schemata;"

echo ""
echo "=========================================="
echo "检查是否有数据（任何表）"
echo "=========================================="
/www/server/pgsql/bin/psql -U quantdinger -d quantdinger -c "SELECT schemaname, tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema');"
