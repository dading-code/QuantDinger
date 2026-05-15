#!/bin/bash
# 检查47.93.6.116数据库内容

echo "=========================================="
echo "检查数据库表数量"
echo "=========================================="
/www/server/pgsql/bin/psql -U quantdinger -d quantdinger -c "SELECT count(*) as table_count FROM information_schema.tables WHERE table_schema = 'public';"

echo ""
echo "=========================================="
echo "列出所有表"
echo "=========================================="
/www/server/pgsql/bin/psql -U quantdinger -d quantdinger -c "\dt"

echo ""
echo "=========================================="
echo "重新导出数据库（包含数据）"
echo "=========================================="
rm -f /tmp/quantdinger_latest.dump
/www/server/pgsql/bin/pg_dump -U quantdinger -d quantdinger --format=custom --compress=9 -f /tmp/quantdinger_latest.dump

echo ""
echo "备份文件大小："
ls -lh /tmp/quantdinger_latest.dump
