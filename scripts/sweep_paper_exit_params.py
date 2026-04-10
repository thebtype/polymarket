from __future__ import annotations

import itertools
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "paper_journal.json"

TP_VALUES = [0.20, 0.30, 0.40, 0.50]
SL_VALUES = [0.15, 0.20, 0.25, 0.35]
HOLD_VALUES = [30, 60, 90, 120]

BASE_ENV = {
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
}


def run_case(tp: float, sl: float, hold: int) -> dict:
    env = os.environ.copy()
    env.update(BASE_ENV)
    env["PAPER_TAKE_PROFIT_PCT"] = str(tp)
    env["PAPER_STOP_LOSS_PCT"] = str(sl)
    env["PAPER_MAX_HOLD_SECONDS"] = str(hold)

    subprocess.run(
        ["python3", "scripts/paper_journal.py"],
        cwd=ROOT,
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    report = json.loads(REPORT_PATH.read_text())
    summary = report["summary"]
    return {
        "take_profit_pct": tp,
        "stop_loss_pct": sl,
        "max_hold_seconds": hold,
        "trade_count": summary["trade_count"],
        "wins": summary["wins"],
        "losses": summary["losses"],
        "win_rate": summary["win_rate"],
        "ending_portfolio": summary["ending_portfolio"],
        "net_profit": summary["net_profit"],
    }


results = [run_case(tp, sl, hold) for tp, sl, hold in itertools.product(TP_VALUES, SL_VALUES, HOLD_VALUES)]
results.sort(key=lambda x: (x["ending_portfolio"], x["win_rate"], x["trade_count"]), reverse=True)
print(json.dumps(results[:15], indent=2))
