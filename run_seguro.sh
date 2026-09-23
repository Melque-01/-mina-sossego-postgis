#!/bin/bash
# Run seguro: backend API isolado (8001) + frontend estático (8000)
# Separe terminal ou use & :
#   ./run_seguro.sh
set -e
echo "=== Subindo backend API 8001 ==="
.venv/bin/python -m backend.api &
API_PID=$!
sleep 1
echo "=== Subindo frontend 8000 (proxy /api -> 8001) ==="
.venv/bin/python servidor.py &
FRONT_PID=$!
echo "API pid $API_PID | FRONT pid $FRONT_PID"
echo " Abra http://localhost:8000/login.html"
echo " API direta http://localhost:8001/api/health"
wait
