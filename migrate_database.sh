#!/bin/bash
# 从47.93.6.116导出数据库并导入到39.105.150.99

SOURCE_SERVER="47.93.6.116"
TARGET_SERVER="39.105.150.99"
DB_NAME="quantdinger"
DB_USER="quantdinger"
DB_PASS="KGFhPRChLYJCy8bB"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="/tmp/quantdinger_source_${TIMESTAMP}.dump"

echo "=========================================="
echo "步骤1: 从源服务器导出数据库"
echo "=========================================="

# 在源服务器上导出数据库
ssh root@${SOURCE_SERVER} "PGPASSWORD='${DB_PASS}' pg_dump -h localhost -U ${DB_USER} -d ${DB_NAME} --format=custom --compress=9 -f ${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    echo "✅ 导出成功"
else
    echo "❌ 导出失败，尝试其他方法..."
    # 尝试不使用-h参数
    ssh root@${SOURCE_SERVER} "PGPASSWORD='${DB_PASS}' pg_dump -U ${DB_USER} -d ${DB_NAME} --format=custom --compress=9 -f ${BACKUP_FILE}"
fi

# 检查文件大小
echo ""
echo "检查备份文件："
ssh root@${SOURCE_SERVER} "ls -lh ${BACKUP_FILE}"

echo ""
echo "=========================================="
echo "步骤2: 传输备份文件到目标服务器"
echo "=========================================="

scp root@${SOURCE_SERVER}:${BACKUP_FILE} /tmp/

if [ $? -eq 0 ]; then
    echo "✅ 传输成功"
    ls -lh /tmp/quantdinger_source_*.dump
else
    echo "❌ 传输失败"
    exit 1
fi

echo ""
echo "=========================================="
echo "步骤3: 导入到目标服务器数据库"
echo "=========================================="

# 先备份当前数据库
echo "正在备份当前数据库..."
podman exec quantdinger-db pg_dump -U quantdinger -d quantdinger --format=custom --compress=9 -f /tmp/quantdinger_backup_before_import_${TIMESTAMP}.dump

# 导入新数据
echo "正在导入数据..."
podman exec -i quantdinger-db pg_restore -U quantdinger -d quantdinger --clean --if-exists < /tmp/$(basename $BACKUP_FILE)

if [ $? -eq 0 ]; then
    echo "✅ 导入成功"
else
    echo "❌ 导入失败"
    echo "可以尝试手动恢复之前的备份"
    exit 1
fi

echo ""
echo "=========================================="
echo "清理临时文件"
echo "=========================================="
ssh root@${SOURCE_SERVER} "rm -f ${BACKUP_FILE}"
rm -f /tmp/$(basename $BACKUP_FILE)

echo ""
echo "=========================================="
echo "完成！数据库迁移成功"
echo "=========================================="
echo "时间: $(date)"
echo "源服务器: ${SOURCE_SERVER}"
echo "目标服务器: ${TARGET_SERVER}"
