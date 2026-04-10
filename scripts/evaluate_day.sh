#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python3 scripts/paper_journal.py
python3 scripts/guardrails.py
python3 scripts/evaluate_day.py
