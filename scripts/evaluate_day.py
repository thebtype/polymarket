from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import json
import statistics

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CONFIG_PATH = ROOT / "config" / "scorecard_metrics.json"
SUMMARY_DIR = ROOT / "reports"
SNAPSHOTS_PATH = DATA_DIR / "market_snapshots.jsonl"
SUMMARY_PATH = SUMMARY_DIR / "daily_summary.md"
SCORECARD_PATH = SUMMARY_DIR / "daily_scorecard.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_snapshots() -> list[dict]:
    if not SNAPSHOTS_PATH.exists():
        return []
    rows = []
    with SNAPSHOTS_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def snapshot_allowed(snapshot: dict, config: dict) -> bool:
    filters = config["filters"]
    if snapshot.get("condition_type") not in filters["allowed_condition_types"]:
        return False
    slug = snapshot.get("slug") or ""
    if not any(slug.startswith(prefix) for prefix in filters["allowed_slug_prefixes"]):
        return False
    if filters.get("exclude_low_confidence") and snapshot.get("parser_confidence") == "low":
        return False
    return True


def infer_updown_outcome(row: dict) -> str | None:
    open_price = row.get("open_reference_price")
    current_price = row.get("binance_mid")
    ttl = row.get("seconds_to_expiry")
    if open_price is None or current_price is None or ttl is None:
        return None
    if ttl > 0:
        return None
    if current_price > open_price:
        return "yes"
    if current_price < open_price:
        return "no"
    return "tie"


def build_market_groups(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        slug = row.get("slug")
        if slug:
            grouped[slug].append(row)
    for slug in grouped:
        grouped[slug].sort(key=lambda row: row.get("captured_at") or "")
    return grouped


def build_market_closes(grouped: dict[str, list[dict]]) -> dict[str, dict]:
    closes: dict[str, dict] = {}
    for slug, items in grouped.items():
        closing_row = max(items, key=lambda row: row.get("captured_at") or "")
        closes[slug] = {
            "question": closing_row.get("question"),
            "close_outcome": infer_updown_outcome(closing_row),
            "close_price": closing_row.get("binance_mid"),
            "open_reference_price": closing_row.get("open_reference_price"),
            "final_seconds_to_expiry": closing_row.get("seconds_to_expiry"),
        }
    return closes


def first_positive_signal(rows: list[dict]) -> dict | None:
    for row in rows:
        gross_edge = row.get("signal", {}).get("gross_edge")
        best_side = row.get("signal", {}).get("best_side")
        if gross_edge is not None and gross_edge > 0 and best_side in {"yes", "no"}:
            return row
    return None


def first_alert_signal(rows: list[dict]) -> dict | None:
    for row in rows:
        signal = row.get("signal", {})
        if signal.get("should_alert") and signal.get("best_side") in {"yes", "no"}:
            return row
    return None


def summarize(rows: list[dict]) -> dict:
    signals = [row["signal"] for row in rows if row.get("signal")]
    net_edges = [sig["net_edge"] for sig in signals if sig.get("net_edge") is not None]
    ttl_values = [row["seconds_to_expiry"] for row in rows if row.get("seconds_to_expiry") is not None]
    blocked_too_close = [
        row for row in rows if "too close to expiry" in (row.get("signal", {}).get("reasons") or [])
    ]
    side_counts = Counter(sig.get("best_side") for sig in signals if sig.get("best_side"))

    grouped = build_market_groups(rows)
    market_closes = build_market_closes(grouped)
    resolved_markets = {slug: data for slug, data in market_closes.items() if data.get("close_outcome") in {"yes", "no"}}

    first_signal_checks = []
    first_alert_checks = []
    first_signal_details = []
    first_alert_details = []

    for slug, market_rows in grouped.items():
        close = resolved_markets.get(slug)
        if not close:
            continue

        signal_row = first_positive_signal(market_rows)
        if signal_row is not None:
            side = signal_row["signal"].get("best_side")
            correct = side == close["close_outcome"]
            first_signal_checks.append(correct)
            first_signal_details.append(
                {
                    "slug": slug,
                    "question": signal_row.get("question"),
                    "captured_at": signal_row.get("captured_at"),
                    "best_side": side,
                    "net_edge": signal_row["signal"].get("net_edge"),
                    "correct": correct,
                    "close_outcome": close["close_outcome"],
                }
            )

        alert_row = first_alert_signal(market_rows)
        if alert_row is not None:
            side = alert_row["signal"].get("best_side")
            correct = side == close["close_outcome"]
            first_alert_checks.append(correct)
            first_alert_details.append(
                {
                    "slug": slug,
                    "question": alert_row.get("question"),
                    "captured_at": alert_row.get("captured_at"),
                    "best_side": side,
                    "net_edge": alert_row["signal"].get("net_edge"),
                    "correct": correct,
                    "close_outcome": close["close_outcome"],
                }
            )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_count": len(rows),
        "signal_count": sum(1 for sig in signals if (sig.get("gross_edge") or 0) > 0),
        "alert_count": sum(1 for sig in signals if sig.get("should_alert")),
        "avg_net_edge": statistics.fmean(net_edges) if net_edges else None,
        "max_net_edge": max(net_edges) if net_edges else None,
        "avg_seconds_to_expiry": statistics.fmean(ttl_values) if ttl_values else None,
        "too_close_to_expiry_count": len(blocked_too_close),
        "best_side_counts": dict(side_counts),
        "sample_questions": sorted({row.get("question") for row in rows if row.get("question")})[:5],
        "resolved_market_count": len(resolved_markets),
        "first_signal_accuracy": (sum(first_signal_checks) / len(first_signal_checks)) if first_signal_checks else None,
        "first_signal_market_count": len(first_signal_checks),
        "first_alert_accuracy": (sum(first_alert_checks) / len(first_alert_checks)) if first_alert_checks else None,
        "first_alert_market_count": len(first_alert_checks),
        "first_signal_details": first_signal_details,
        "first_alert_details": first_alert_details,
        "resolved_markets": resolved_markets,
    }


def render_summary(scorecard: dict) -> str:
    def fmt(value: float | None, digits: int = 4) -> str:
        if value is None:
            return "n/a"
        return f"{value:.{digits}f}"

    lines = [
        "# Daily Bot Summary",
        "",
        f"Generated at: {scorecard['generated_at']}",
        "",
        "## Scorecard",
        f"- Snapshots evaluated: {scorecard['snapshot_count']}",
        f"- Positive-edge signals: {scorecard['signal_count']}",
        f"- Alerts triggered: {scorecard['alert_count']}",
        f"- Average net edge: {fmt(scorecard['avg_net_edge'])}",
        f"- Max net edge: {fmt(scorecard['max_net_edge'])}",
        f"- Average seconds to expiry: {fmt(scorecard['avg_seconds_to_expiry'], 1)}",
        f"- Too-close-to-expiry blocks: {scorecard['too_close_to_expiry_count']}",
        f"- Resolved markets: {scorecard['resolved_market_count']}",
        f"- First positive-signal accuracy: {fmt(scorecard['first_signal_accuracy'])}",
        f"- Markets with first positive signal: {scorecard['first_signal_market_count']}",
        f"- First alert accuracy: {fmt(scorecard['first_alert_accuracy'])}",
        f"- Markets with first alert: {scorecard['first_alert_market_count']}",
        "",
        "## Best side mix",
    ]

    if scorecard["best_side_counts"]:
        for side, count in sorted(scorecard["best_side_counts"].items()):
            lines.append(f"- {side}: {count}")
    else:
        lines.append("- none")

    lines.extend([
        "",
        "## Sample markets",
    ])
    if scorecard["sample_questions"]:
        for question in scorecard["sample_questions"]:
            lines.append(f"- {question}")
    else:
        lines.append("- none")

    lines.extend([
        "",
        "## First positive signals",
    ])
    if scorecard["first_signal_details"]:
        for item in scorecard["first_signal_details"]:
            lines.append(
                f"- {item['slug']}: side={item['best_side']}, outcome={item['close_outcome']}, net_edge={item['net_edge']}, correct={item['correct']}"
            )
    else:
        lines.append("- none yet")

    lines.extend([
        "",
        "## First alerts",
    ])
    if scorecard["first_alert_details"]:
        for item in scorecard["first_alert_details"]:
            lines.append(
                f"- {item['slug']}: side={item['best_side']}, outcome={item['close_outcome']}, net_edge={item['net_edge']}, correct={item['correct']}"
            )
    else:
        lines.append("- none yet")

    return "\n".join(lines) + "\n"


def main() -> int:
    config = load_config()
    snapshots = load_snapshots()
    filtered = [row for row in snapshots if snapshot_allowed(row, config)]
    scorecard = summarize(filtered)

    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    SCORECARD_PATH.write_text(json.dumps(scorecard, indent=2) + "\n", encoding="utf-8")
    SUMMARY_PATH.write_text(render_summary(scorecard), encoding="utf-8")

    print(json.dumps(scorecard, indent=2))
    print(f"\nWrote {SCORECARD_PATH}")
    print(f"Wrote {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
