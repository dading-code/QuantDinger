#!/bin/bash
# 从47.93.6.116远程导出数据库（在本地执行）

SOURCE_HOST="47.93.6.116"
DB_NAME="quantdinger"
DB_USER="quantdinger"
DB_PASS="KGFhPRChLYJCy8bB"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="d:/www/workai/QuantDinger/backups/quantdinger_from_47_${TIMESTAMP}.dump"

echo "=========================================="
echo "从47.93.6.116远程导出数据库"
echo "=========================================="
echo "主机: ${SOURCE_HOST}"
echo "数据库: ${DB_NAME}"
echo "用户: ${DB_USER}"
echo ""

# 检查pg_dump是否可用
which pg_dump > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ 错误: 未找到pg_dump命令"
    echo "请安装PostgreSQL客户端工具"
    exit 1
fi

echo "正在导出..."
PGPASSWORD="${DB_PASS}" pg_dump -h ${SOURCE_HOST} -U ${DB_USER} -d ${DB_NAME} --format=custom --compress=9 -f "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 导出成功!"
    echo "文件: ${BACKUP_FILE}"
    ls -lh "${BACKUP_FILE}"
else
    echo ""
    echo "❌ 导出失败"
    echo "可能的原因:"
    echo "1. 47.93.6.116的PostgreSQL不允许远程连接"
    echo "2. 防火墙阻止了5432端口"
    echo "3. pg_hba.conf配置不允许该用户远程访问"
    exit 1
fi
