#!/bin/bash
# 测试连接到47.93.6.116的数据库

echo "测试连接..."
PGPASSWORD="KGFhPRChLYJCy8bB" psql -h 47.93.6.116 -U quantdinger -d quantdinger -c "SELECT version();"

if [ $? -eq 0 ]; then
    echo "✅ 连接成功！"
else
    echo "❌ 连接失败"
fi
