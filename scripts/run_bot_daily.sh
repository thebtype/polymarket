#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/logs"
STAMP="$(date +%F)"
LOG_FILE="$LOG_DIR/polymarket_gap_bot_${STAMP}.out"
LATEST_LINK="$LOG_DIR/polymarket_gap_bot.out"
PID_FILE="$ROOT/run/polymarket_gap_bot.pid"

mkdir -p "$LOG_DIR" "$ROOT/run"
touch "$LOG_FILE"
ln -sfn "$(basename "$LOG_FILE")" "$LATEST_LINK"

if [[ -f "$PID_FILE" ]]; then
  OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$OLD_PID" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Bot already running with PID $OLD_PID"
    echo "Log: $LOG_FILE"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

cd "$ROOT"
nohup env SERIES_SEARCH_LIMIT="${SERIES_SEARCH_LIMIT:-1600}" python3 -m polymarket_gap_bot.main >> "$LOG_FILE" 2>&1 &
NEW_PID=$!
printf '%s\n' "$NEW_PID" > "$PID_FILE"

echo "Started polymarket gap bot"
echo "PID: $NEW_PID"
echo "Log: $LOG_FILE"
