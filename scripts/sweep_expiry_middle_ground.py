from __future__ import annotations

import itertools
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "paper_journal.json"

NET_EDGES = [0.16, 0.18, 0.20]
MAX_ENTRY_PRICES = [0.50, 0.51, 0.52]
MAX_SPREADS = [0.015, 0.02]
MIN_TTLS = [90, 120]

BASE_ENV = {
    "PAPER_RISK_PCT": "0.02",
    "PAPER_SIDE": "both",
    "PAPER_ENTRY_LAG_SECONDS": "25",
    "PAPER_ENTRY_SLIPPAGE": "0.03",
    "PAPER_MAX_CONSECUTIVE_LOSSES": "5",
    "PAPER_MAX_DAILY_LOSS_PCT": "0.10",
    "PAPER_EXIT_MODE": "expiry",
}


def run_case(net_edge: float, max_entry: float, max_spread: float, min_ttl: int) -> dict:
    env = os.environ.copy()
    env.update(BASE_ENV)
    env["PAPER_MIN_NET_EDGE"] = str(net_edge)
    env["PAPER_MAX_ENTRY_PRICE"] = str(max_entry)
    env["PAPER_MAX_SPREAD"] = str(max_spread)
    env["PAPER_MIN_SECONDS_TO_EXPIRY_AT_ENTRY"] = str(min_ttl)

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
        "min_net_edge": net_edge,
        "max_entry_price": max_entry,
        "max_spread": max_spread,
        "min_seconds_to_expiry": min_ttl,
        "trade_count": summary["trade_count"],
        "wins": summary["wins"],
        "losses": summary["losses"],
        "win_rate": summary["win_rate"],
        "ending_portfolio": summary["ending_portfolio"],
        "net_profit": summary["net_profit"],
    }


results = [run_case(*params) for params in itertools.product(NET_EDGES, MAX_ENTRY_PRICES, MAX_SPREADS, MIN_TTLS)]
results.sort(key=lambda x: (x["ending_portfolio"], x["trade_count"], x["win_rate"]), reverse=True)
print(json.dumps(results[:15], indent=2))
