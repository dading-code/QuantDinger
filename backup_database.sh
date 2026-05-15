#!/bin/bash
# QuantDinger 数据库备份脚本
# 用法: bash backup_database.sh [保留天数]

set -e

BACKUP_DIR="/opt/quantdinger/backups"
RETENTION_DAYS=${1:-30}  # 默认保留30天
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="quantdinger_backup_${TIMESTAMP}.dump"

echo "=========================================="
echo "QuantDinger 数据库备份"
echo "=========================================="
echo "时间: $(date)"
echo "备份文件: $BACKUP_FILE"
echo "保留天数: $RETENTION_DAYS 天"
echo ""

# 创建备份目录
mkdir -p $BACKUP_DIR

# 执行备份
echo "正在备份数据库..."
podman exec quantdinger-db pg_dump -U quantdinger -d quantdinger \
    --format=custom \
    --compress=9 \
    --file=/tmp/$BACKUP_FILE

# 从容器复制到宿主机
echo "正在复制备份文件..."
podman cp quantdinger-db:/tmp/$BACKUP_FILE $BACKUP_DIR/

# 删除容器内的临时文件
podman exec quantdinger-db rm -f /tmp/$BACKUP_FILE

# 检查备份文件大小
BACKUP_SIZE=$(ls -lh $BACKUP_DIR/$BACKUP_FILE | awk '{print $5}')
echo ""
echo "✅ 备份完成!"
echo "   文件: $BACKUP_DIR/$BACKUP_FILE"
echo "   大小: $BACKUP_SIZE"

# 清理旧备份
echo ""
echo "清理 ${RETENTION_DAYS} 天前的旧备份..."
find $BACKUP_DIR -name "quantdinger_backup_*.dump" -mtime +$RETENTION_DAYS -delete
REMAINING=$(ls -1 $BACKUP_DIR/quantdinger_backup_*.dump 2>/dev/null | wc -l)
echo "   剩余备份数量: $REMAINING"

echo ""
echo "=========================================="
echo "备份历史:"
echo "=========================================="
ls -lh $BACKUP_DIR/quantdinger_backup_*.dump 2>/dev/null || echo "无备份文件"
