from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "paper_journal.json"

SCENARIOS = [
    (
        "old_expiry",
        {
            "PAPER_RISK_PCT": "0.02",
            "PAPER_SIDE": "yes",
            "PAPER_MIN_NET_EDGE": "0.12",
            "PAPER_ENTRY_LAG_SECONDS": "10",
            "PAPER_ENTRY_SLIPPAGE": "0.00",
            "PAPER_MAX_ENTRY_PRICE": "0.55",
            "PAPER_MAX_SPREAD": "0.03",
            "PAPER_MIN_SECONDS_TO_EXPIRY_AT_ENTRY": "60",
            "PAPER_MAX_CONSECUTIVE_LOSSES": "999",
            "PAPER_MAX_DAILY_LOSS_PCT": "1.0",
            "PAPER_EXIT_MODE": "expiry",
        },
    ),
    (
        "harsher_expiry",
        {
            "PAPER_RISK_PCT": "0.02",
            "PAPER_SIDE": "both",
            "PAPER_MIN_NET_EDGE": "0.20",
            "PAPER_ENTRY_LAG_SECONDS": "25",
            "PAPER_ENTRY_SLIPPAGE": "0.03",
            "PAPER_MAX_ENTRY_PRICE": "0.50",
            "PAPER_MAX_SPREAD": "0.015",
            "PAPER_MIN_SECONDS_TO_EXPIRY_AT_ENTRY": "120",
            "PAPER_MAX_CONSECUTIVE_LOSSES": "5",
            "PAPER_MAX_DAILY_LOSS_PCT": "0.10",
            "PAPER_EXIT_MODE": "expiry",
        },
    ),
    (
        "early_exit_best_found",
        {
            "PAPER_RISK_PCT": "0.02",
            "PAPER_SIDE": "both",
            "PAPER_MIN_NET_EDGE": "0.18",
            "PAPER_ENTRY_LAG_SECONDS": "25",
            "PAPER_ENTRY_SLIPPAGE": "0.02",
            "PAPER_MAX_ENTRY_PRICE": "0.52",
            "PAPER_MAX_SPREAD": "0.02",
            "PAPER_MIN_SECONDS_TO_EXPIRY_AT_ENTRY": "90",
            "PAPER_MAX_CONSECUTIVE_LOSSES": "5",
            "PAPER_MAX_DAILY_LOSS_PCT": "0.10",
            "PAPER_EXIT_MODE": "early",
            "PAPER_TAKE_PROFIT_PCT": "0.20",
            "PAPER_STOP_LOSS_PCT": "0.15",
            "PAPER_MAX_HOLD_SECONDS": "120",
        },
    ),
]

results = []
for name, overrides in SCENARIOS:
    env = os.environ.copy()
    env.update(overrides)
    subprocess.run(
        ["python3", "scripts/paper_journal.py"],
        cwd=ROOT,
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    report = json.loads(REPORT_PATH.read_text())
    results.append(
        {
            "scenario": name,
            "summary": report["summary"],
            "assumptions": report["assumptions"],
        }
    )

print(json.dumps(results, indent=2))
