#!/bin/bash
curl -v http://127.0.0.1:5000/api/health 2>&1 | head -30
