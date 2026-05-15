#!/bin/bash
cd /opt/quantdinger/QuantDinger/backend_api_python
source .venv/bin/activate
python3 -c "import redis; r = redis.Redis(host='47.93.6.116', port=6379, password='Redis@2026', socket_timeout=3); print('Ping:', r.ping())"
