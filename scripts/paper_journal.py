from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import csv
import json
import os

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"
SNAPSHOTS_PATH = DATA_DIR / "market_snapshots.jsonl"
JOURNAL_PATH = REPORTS_DIR / "paper_journal.json"
SUMMARY_PATH = REPORTS_DIR / "paper_journal_summary.md"

STARTING_PORTFOLIO = float(os.getenv("PAPER_STARTING_PORTFOLIO", "1000"))
RISK_PCT = float(os.getenv("PAPER_RISK_PCT", "0.02"))
TARGET_SIDE = os.getenv("PAPER_SIDE", "both").lower()
MIN_NET_EDGE = float(os.getenv("PAPER_MIN_NET_EDGE", "0.16"))
ENTRY_LAG_SECONDS = int(os.getenv("PAPER_ENTRY_LAG_SECONDS", "25"))
ENTRY_SLIPPAGE = float(os.getenv("PAPER_ENTRY_SLIPPAGE", "0.03"))
MAX_ENTRY_PRICE = float(os.getenv("PAPER_MAX_ENTRY_PRICE", "0.52"))
MAX_SPREAD = float(os.getenv("PAPER_MAX_SPREAD", "0.02"))
MIN_SECONDS_TO_EXPIRY_AT_ENTRY = int(os.getenv("PAPER_MIN_SECONDS_TO_EXPIRY_AT_ENTRY", "120"))
MAX_CONSECUTIVE_LOSSES = int(os.getenv("PAPER_MAX_CONSECUTIVE_LOSSES", "5"))
MAX_DAILY_LOSS_PCT = float(os.getenv("PAPER_MAX_DAILY_LOSS_PCT", "0.10"))
EXIT_MODE = os.getenv("PAPER_EXIT_MODE", "expiry").lower()
TAKE_PROFIT_PCT = float(os.getenv("PAPER_TAKE_PROFIT_PCT", "0.20"))
STOP_LOSS_PCT = float(os.getenv("PAPER_STOP_LOSS_PCT", "0.15"))
MAX_HOLD_SECONDS = int(os.getenv("PAPER_MAX_HOLD_SECONDS", "120"))
ALLOWED_CONDITION_TYPES = {"range_close_vs_open"}
ALLOWED_SLUG_PREFIXES = ("btc-updown-5m-",)


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_snapshots() -> list[dict]:
    rows: list[dict] = []
    if not SNAPSHOTS_PATH.exists():
        return rows
    with SNAPSHOTS_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            signal = row.get("signal") or {}
            row["captured_at_dt"] = parse_dt(row.get("captured_at"))
            row["end_date_dt"] = parse_dt(row.get("end_date"))
            row["signal"] = signal
            rows.append(row)
    return rows


def allowed(row: dict) -> bool:
    slug = row.get("slug") or ""
    return (
        row.get("condition_type") in ALLOWED_CONDITION_TYPES
        and any(slug.startswith(prefix) for prefix in ALLOWED_SLUG_PREFIXES)
        and row.get("parser_confidence") != "low"
    )


def outcome_from_row(row: dict) -> str | None:
    open_price = row.get("open_reference_price")
    current_price = row.get("binance_mid")
    ttl = row.get("seconds_to_expiry")
    if open_price is None or current_price is None or ttl is None or ttl > 0:
        return None
    if current_price > open_price:
        return "yes"
    if current_price < open_price:
        return "no"
    return "tie"


def quote_for_side(row: dict, side: str, kind: str) -> float | None:
    if side == "yes":
        return row.get("yes_ask") if kind == "ask" else row.get("yes_bid")
    return row.get("no_ask") if kind == "ask" else row.get("no_bid")


def build_journal(rows: list[dict]) -> dict:
    filtered = [row for row in rows if allowed(row)]
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in filtered:
        slug = row.get("slug")
        if slug:
            grouped[slug].append(row)
    for slug in grouped:
        grouped[slug].sort(key=lambda r: r["captured_at_dt"] or datetime.min.replace(tzinfo=timezone.utc))

    portfolio = STARTING_PORTFOLIO
    trades: list[dict] = []
    consecutive_losses = 0
    current_day = None
    day_start_portfolio = STARTING_PORTFOLIO

    for slug, items in sorted(grouped.items(), key=lambda kv: kv[1][0]["captured_at_dt"] or datetime.min.replace(tzinfo=timezone.utc)):
        signal_row = None
        signal_side = None
        for row in items:
            sig = row.get("signal") or {}
            if not sig.get("should_alert"):
                continue
            best_side = sig.get("best_side")
            if best_side not in {"yes", "no"}:
                continue
            if TARGET_SIDE != "both" and best_side != TARGET_SIDE:
                continue
            net_edge = sig.get("net_edge")
            if net_edge is None or net_edge < MIN_NET_EDGE:
                continue
            signal_row = row
            signal_side = best_side
            break
        if signal_row is None or signal_side is None:
            continue

        signal_time = signal_row["captured_at_dt"]
        if signal_time is None:
            continue
        trade_day = signal_time.date()
        if current_day != trade_day:
            current_day = trade_day
            day_start_portfolio = portfolio
            consecutive_losses = 0

        daily_loss_limit = day_start_portfolio * MAX_DAILY_LOSS_PCT
        if (day_start_portfolio - portfolio) >= daily_loss_limit:
            continue
        if consecutive_losses >= MAX_CONSECUTIVE_LOSSES:
            continue

        entry_time = signal_time + timedelta(seconds=ENTRY_LAG_SECONDS)

        entry_row = None
        for row in items:
            captured = row.get("captured_at_dt")
            if captured is not None and captured >= entry_time:
                entry_row = row
                break
        if entry_row is None:
            continue

        settlement_row = None
        for row in reversed(items):
            if outcome_from_row(row) in {"yes", "no", "tie"}:
                settlement_row = row
                break
        if settlement_row is None:
            continue

        outcome = outcome_from_row(settlement_row)
        if outcome not in {"yes", "no"}:
            continue

        raw_entry_price = quote_for_side(entry_row, signal_side, "ask")
        if raw_entry_price is None or raw_entry_price <= 0 or raw_entry_price >= 1:
            continue
        entry_price = min(raw_entry_price + ENTRY_SLIPPAGE, 0.99)
        if entry_price > MAX_ENTRY_PRICE:
            continue
        spread = entry_row.get("spread")
        if spread is None or spread > MAX_SPREAD:
            continue
        seconds_to_expiry = entry_row.get("seconds_to_expiry")
        if seconds_to_expiry is None or seconds_to_expiry < MIN_SECONDS_TO_EXPIRY_AT_ENTRY:
            continue

        take_profit_price = min(entry_price * (1 + TAKE_PROFIT_PCT), 0.99)
        stop_loss_price = max(entry_price * (1 - STOP_LOSS_PCT), 0.01)
        exit_row = settlement_row
        exit_price = 1.0 if outcome == signal_side else 0.0
        exit_reason = "expiry"

        if EXIT_MODE != "expiry":
            max_exit_time = entry_time + timedelta(seconds=MAX_HOLD_SECONDS)
            for row in items:
                captured = row.get("captured_at_dt")
                if captured is None or captured < entry_time:
                    continue
                current_bid = quote_for_side(row, signal_side, "bid")
                if current_bid is None:
                    continue
                if current_bid >= take_profit_price:
                    exit_row = row
                    exit_price = current_bid
                    exit_reason = "take_profit"
                    break
                if current_bid <= stop_loss_price:
                    exit_row = row
                    exit_price = current_bid
                    exit_reason = "stop_loss"
                    break
                if captured >= max_exit_time:
                    exit_row = row
                    exit_price = current_bid
                    exit_reason = "timeout"
                    break

        stake = round(portfolio * RISK_PCT, 2)
        if stake <= 0:
            continue
        contracts = stake / entry_price
        proceeds = contracts * exit_price
        pnl = round(proceeds - stake, 2)
        portfolio = round(portfolio + pnl, 2)
        consecutive_losses = 0 if pnl > 0 else consecutive_losses + 1

        trades.append(
            {
                "slug": slug,
                "question": signal_row.get("question"),
                "signal_time": signal_time.isoformat(),
                "entry_time": entry_row["captured_at_dt"].isoformat() if entry_row.get("captured_at_dt") else None,
                "entry_lag_seconds": ENTRY_LAG_SECONDS,
                "side": signal_side,
                "signal_net_edge": signal_row.get("signal", {}).get("net_edge"),
                "raw_entry_price": raw_entry_price,
                "entry_slippage": ENTRY_SLIPPAGE,
                "entry_price": entry_price,
                "take_profit_price": round(take_profit_price, 4),
                "stop_loss_price": round(stop_loss_price, 4),
                "max_hold_seconds": MAX_HOLD_SECONDS,
                "stake": stake,
                "contracts": round(contracts, 6),
                "outcome": outcome,
                "exit_time": exit_row["captured_at_dt"].isoformat() if exit_row.get("captured_at_dt") else None,
                "exit_price": exit_price,
                "exit_reason": exit_reason,
                "won": pnl > 0,
                "pnl": pnl,
                "portfolio_after": portfolio,
            }
        )

    wins = sum(1 for t in trades if t["won"])
    losses = len(trades) - wins
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "assumptions": {
            "starting_portfolio": STARTING_PORTFOLIO,
            "risk_pct_per_trade": RISK_PCT,
            "side": TARGET_SIDE,
            "min_net_edge": MIN_NET_EDGE,
            "entry_lag_seconds": ENTRY_LAG_SECONDS,
            "entry_slippage": ENTRY_SLIPPAGE,
            "max_entry_price": MAX_ENTRY_PRICE,
            "max_spread": MAX_SPREAD,
            "min_seconds_to_expiry_at_entry": MIN_SECONDS_TO_EXPIRY_AT_ENTRY,
            "max_daily_loss_pct": MAX_DAILY_LOSS_PCT,
            "max_consecutive_losses": MAX_CONSECUTIVE_LOSSES,
            "exit_mode": EXIT_MODE,
            "take_profit_pct": TAKE_PROFIT_PCT,
            "stop_loss_pct": STOP_LOSS_PCT,
            "max_hold_seconds": MAX_HOLD_SECONDS,
            "pricing": "buy at delayed ask plus slippage and settle at expiry" if EXIT_MODE == "expiry" else "buy at delayed ask plus slippage, try to exit early at take-profit or stop-loss, otherwise timeout or settle at expiry",
        },
        "summary": {
            "trade_count": len(trades),
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / len(trades)) if trades else None,
            "ending_portfolio": portfolio,
            "net_profit": round(portfolio - STARTING_PORTFOLIO, 2),
        },
        "trades": trades,
    }


def render_summary(report: dict) -> str:
    s = report["summary"]
    a = report["assumptions"]
    lines = [
        "# Paper Journal Summary",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        "## Assumptions",
        f"- Starting portfolio: ${a['starting_portfolio']:.2f}",
        f"- Risk per trade: {a['risk_pct_per_trade'] * 100:.2f}%",
        f"- Side: {a['side']}",
        f"- Min net edge: {a['min_net_edge']:.2f}",
        f"- Entry lag: {a['entry_lag_seconds']}s",
        f"- Entry slippage: {a['entry_slippage']:.2f}",
        f"- Max entry price: {a['max_entry_price']:.2f}",
        f"- Max spread: {a['max_spread']:.2f}",
        f"- Min seconds to expiry at entry: {a['min_seconds_to_expiry_at_entry']}",
        f"- Max daily loss: {a['max_daily_loss_pct'] * 100:.2f}% of portfolio",
        f"- Max consecutive losses: {a['max_consecutive_losses']}",
        f"- Exit mode: {a['exit_mode']}",
        f"- Take profit: {a['take_profit_pct'] * 100:.2f}%",
        f"- Stop loss: {a['stop_loss_pct'] * 100:.2f}%",
        f"- Max hold time: {a['max_hold_seconds']}s",
        f"- Pricing: {a['pricing']}",
        "",
        "## Results",
        f"- Trades: {s['trade_count']}",
        f"- Wins: {s['wins']}",
        f"- Losses: {s['losses']}",
        f"- Win rate: {s['win_rate']:.4f}" if s['win_rate'] is not None else "- Win rate: n/a",
        f"- Ending portfolio: ${s['ending_portfolio']:.2f}",
        f"- Net profit: ${s['net_profit']:.2f}",
        "",
        "## Recent trades",
    ]
    recent = report["trades"][-10:]
    if recent:
        for trade in recent:
            lines.append(
                f"- {trade['entry_time']} {trade['slug']} side={trade['side']} entry={trade['entry_price']:.4f} stake=${trade['stake']:.2f} outcome={trade['outcome']} pnl=${trade['pnl']:.2f} portfolio=${trade['portfolio_after']:.2f}"
            )
    else:
        lines.append("- none yet")
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = build_journal(load_snapshots())
    JOURNAL_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    SUMMARY_PATH.write_text(render_summary(report), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    print(f"Wrote {JOURNAL_PATH}")
    print(f"Wrote {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
