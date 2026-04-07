#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$ROOT/run/polymarket_gap_bot.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No pid file found"
  exit 0
fi

PID="$(cat "$PID_FILE")"
if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  echo "Stopped bot PID $PID"
else
  echo "PID $PID is not running"
fi

rm -f "$PID_FILE"
