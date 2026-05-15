#!/usr/bin/env python3
import socket
try:
    s = socket.socket()
    s.settimeout(2)
    result = s.connect_ex(('quantdinger-db', 5432))
    if result == 0:
        print('Port 5432 OPEN')
    else:
        print('Port 5432 CLOSED')
    s.close()
except Exception as e:
    print(f'Error: {e}')
