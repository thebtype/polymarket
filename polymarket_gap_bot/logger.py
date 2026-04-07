from __future__ import annotations

from csv import DictWriter
import json
from pathlib import Path

from .config import Settings
from .models import MarketSnapshot, SignalEvaluation


class EventLogger:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._ensure_signal_header()

    def _ensure_signal_header(self) -> None:
        path = self.settings.signals_path
        if path.exists():
            return
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = DictWriter(
                handle,
                fieldnames=[
                    "captured_at",
                    "market_id",
                    "question",
                    "best_side",
                    "fair_yes_probability",
                    "edge_yes_buy",
                    "edge_no_buy",
                    "gross_edge",
                    "net_edge",
                    "confidence",
                    "should_alert",
                    "reasons",
                ],
            )
            writer.writeheader()

    def log_snapshot(self, snapshot: MarketSnapshot, signal: SignalEvaluation) -> None:
        payload = snapshot.to_dict() | {"signal": signal.to_dict()}
        with self.settings.snapshots_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def log_signal(self, snapshot: MarketSnapshot, signal: SignalEvaluation) -> None:
        with self.settings.signals_path.open("a", newline="", encoding="utf-8") as handle:
            writer = DictWriter(handle, fieldnames=[
                "captured_at",
                "market_id",
                "question",
                "best_side",
                "fair_yes_probability",
                "edge_yes_buy",
                "edge_no_buy",
                "gross_edge",
                "net_edge",
                "confidence",
                "should_alert",
                "reasons",
            ])
            writer.writerow(
                {
                    "captured_at": snapshot.captured_at.isoformat(),
                    "market_id": snapshot.market_id,
                    "question": snapshot.question,
                    "best_side": signal.best_side,
                    "fair_yes_probability": signal.fair_yes_probability,
                    "edge_yes_buy": signal.edge_yes_buy,
                    "edge_no_buy": signal.edge_no_buy,
                    "gross_edge": signal.gross_edge,
                    "net_edge": signal.net_edge,
                    "confidence": signal.confidence,
                    "should_alert": signal.should_alert,
                    "reasons": "; ".join(signal.reasons),
                }
            )
