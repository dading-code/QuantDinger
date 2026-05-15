#!/usr/bin/env python3
"""测试数据库连接"""
import socket

try:
    s = socket.socket()
    s.settimeout(2)
    result = s.connect_ex(('quantdinger-db', 5432))
    if result == 0:
        print('✅ Port 5432 OPEN - 可以连接到quantdinger-db')
    else:
        print('❌ Port 5432 CLOSED - 无法连接到quantdinger-db')
    s.close()
except Exception as e:
    print(f'❌ 连接失败: {e}')
