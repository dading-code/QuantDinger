#!/usr/bin/env python3
"""Test if port 8765 is listening"""
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    result = s.connect_ex(('127.0.0.1', 8765))
    if result == 0:
        print("Port 8765: LISTENING")
    else:
        print(f"Port 8765: NOT LISTENING (code: {result})")
except Exception as e:
    print(f"Error: {e}")
finally:
    s.close()
