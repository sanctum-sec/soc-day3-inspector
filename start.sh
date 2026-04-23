#!/bin/bash
set -a
source ~/.soc_env
set +a

export ADMIN_USER="${ADMIN_USER:-admin}"
export ADMIN_PASS="${ADMIN_PASS:-inspector-admin-2026}"

cd /home/ubuntu/app

# Main app: port 8000
uvicorn main:app --host 0.0.0.0 --port 8000 &

# Admin app: port 8001
uvicorn admin.app:admin_app --host 0.0.0.0 --port 8001 &

wait
