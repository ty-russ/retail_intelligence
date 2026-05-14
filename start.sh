#!/usr/bin/env bash
# Launcher for the HF Spaces container.
#
# 1. Backend (FastAPI) on 127.0.0.1:8000 — internal only.
# 2. Streamlit on 0.0.0.0:7860 — HF Spaces' public port.
# Streamlit's API_BASE points at localhost:8000 by default.
set -euo pipefail

# Quieter Streamlit and uvicorn logs
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
export STREAMLIT_SERVER_FILE_WATCHER_TYPE=none
export PYTHONPATH=/home/user/app

echo "[start] Booting FastAPI backend on 127.0.0.1:8000..."
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level warning &
BACKEND_PID=$!

# Give uvicorn a moment to bind before Streamlit starts asking it questions.
sleep 3

# Forward signals so the container shuts down cleanly when HF stops it.
trap 'echo "[start] Shutting down..."; kill -TERM $BACKEND_PID 2>/dev/null || true; exit 0' SIGTERM SIGINT

echo "[start] Booting Streamlit on 0.0.0.0:7860..."
exec streamlit run streamlit_app/app.py \
    --server.port 7860 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false \
    --browser.gatherUsageStats false
