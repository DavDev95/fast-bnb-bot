#!/usr/bin/env bash
# Run the bot 24/7 WITHOUT root / systemd.
# Auto-restarts on crash. Launch it detached so it survives logout:
#
#   nohup ./deploy/run-forever.sh > bot.out 2>&1 &
#
# Stop it:   pkill -f "main.py"
# Logs:      tail -f bot.out

set -u
cd "$(dirname "$0")/.." || exit 1

# Pick the venv python if present, else system python3.
PY="python3"
[ -x ".venv/bin/python" ] && PY=".venv/bin/python"

while true; do
    echo "[run-forever] starting bot at $(date)"
    "$PY" main.py
    code=$?
    echo "[run-forever] bot exited (code $code). Restarting in 5s..."
    sleep 5
done
