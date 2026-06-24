#!/usr/bin/env bash
# Gunluk market verisi guncelleme scripti.
# Crontab tarafindan tetiklenir, uvicorn'dan bagimsiz calisir.

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$PROJECT_DIR/venv/bin/python"
LOG="$PROJECT_DIR/data/pipeline.log"

echo "$(date -u '+%Y-%m-%d %H:%M:%S') UTC -- cron tetiklendi" >> "$LOG"

cd "$PROJECT_DIR" && "$PYTHON" -m data.pipeline --update >> "$LOG" 2>&1
