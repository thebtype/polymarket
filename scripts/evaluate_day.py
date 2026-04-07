from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json
import statistics
import sys

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


def summarize(rows: list[dict]) -> dict:
    signals = [row["signal"] for row in rows if row.get("signal")]
    net_edges = [sig["net_edge"] for sig in signals if sig.get("net_edge") is not None]
    ttl_values = [row["seconds_to_expiry"] for row in rows if row.get("seconds_to_expiry") is not None]
    blocked_too_close = [
        row for row in rows if "too close to expiry" in (row.get("signal", {}).get("reasons") or [])
    ]
    side_counts = Counter(sig.get("best_side") for sig in signals if sig.get("best_side"))

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
