from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import os

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
GUARDRAILS_PATH = REPORTS_DIR / "guardrails.json"
GUARDRAILS_SUMMARY_PATH = REPORTS_DIR / "guardrails.md"


@dataclass(slots=True)
class Guardrails:
    mode: str = os.getenv("EXECUTION_MODE", "paper")
    reference_portfolio: float = float(os.getenv("REFERENCE_PORTFOLIO", "1000"))
    max_daily_loss_pct: float = float(os.getenv("MAX_DAILY_LOSS_PCT", "0.10"))
    max_position_size_pct: float = float(os.getenv("MAX_POSITION_SIZE_PCT", "0.02"))
    max_consecutive_losses: int = int(os.getenv("MAX_CONSECUTIVE_LOSSES", "5"))
    min_net_edge_live: float = float(os.getenv("MIN_NET_EDGE_LIVE", "0.20"))
    min_seconds_to_expiry_live: int = int(os.getenv("MIN_SECONDS_TO_EXPIRY_LIVE", "120"))
    max_spread_live: float = float(os.getenv("MAX_SPREAD_LIVE", "0.015"))
    kill_switch_enabled: bool = os.getenv("KILL_SWITCH_ENABLED", "true").lower() == "true"
    require_manual_reenable_after_kill: bool = os.getenv("REQUIRE_MANUAL_REENABLE_AFTER_KILL", "true").lower() == "true"
    dedicated_wallet_required: bool = os.getenv("DEDICATED_WALLET_REQUIRED", "true").lower() == "true"
    separate_execution_module_required: bool = os.getenv("SEPARATE_EXECUTION_MODULE_REQUIRED", "true").lower() == "true"
    notes: list[str] | None = None


def build_guardrails() -> dict:
    g = Guardrails(
        notes=[
            "Do not go live from monitor code directly; require a separate execution module.",
            "Stop trading immediately after hitting max daily loss, max consecutive losses, or any unexpected fill behavior.",
            "Position sizing should scale with current portfolio, not fixed dollars.",
            "Require a dedicated wallet with isolated permissions before any live order flow.",
            "Manual re-enable required after any kill-switch trigger.",
        ]
    )
    data = asdict(g)
    data["max_daily_loss"] = round(data["reference_portfolio"] * data["max_daily_loss_pct"], 2)
    data["max_position_size"] = round(data["reference_portfolio"] * data["max_position_size_pct"], 2)
    return data


def render_summary(guardrails: dict) -> str:
    lines = [
        "# Trading Guardrails",
        "",
        f"- Mode: {guardrails['mode']}",
        f"- Reference portfolio: ${guardrails['reference_portfolio']:.2f}",
        f"- Max daily loss: {guardrails['max_daily_loss_pct'] * 100:.2f}% (${guardrails['max_daily_loss']:.2f} at current reference portfolio)",
        f"- Max position size: {guardrails['max_position_size_pct'] * 100:.2f}% (${guardrails['max_position_size']:.2f} at current reference portfolio)",
        f"- Max consecutive losses: {guardrails['max_consecutive_losses']}",
        f"- Min net edge for live trading: {guardrails['min_net_edge_live']:.2f}",
        f"- Min seconds to expiry for live trading: {guardrails['min_seconds_to_expiry_live']}",
        f"- Max spread for live trading: {guardrails['max_spread_live']:.3f}",
        f"- Kill switch enabled: {guardrails['kill_switch_enabled']}",
        f"- Manual re-enable after kill: {guardrails['require_manual_reenable_after_kill']}",
        f"- Dedicated wallet required: {guardrails['dedicated_wallet_required']}",
        f"- Separate execution module required: {guardrails['separate_execution_module_required']}",
        "",
        "## Operating notes",
    ]
    for note in guardrails.get("notes") or []:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    guardrails = build_guardrails()
    GUARDRAILS_PATH.write_text(json.dumps(guardrails, indent=2) + "\n", encoding="utf-8")
    GUARDRAILS_SUMMARY_PATH.write_text(render_summary(guardrails), encoding="utf-8")
    print(json.dumps(guardrails, indent=2))
    print(f"Wrote {GUARDRAILS_PATH}")
    print(f"Wrote {GUARDRAILS_SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
