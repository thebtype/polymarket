from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class BinanceTick:
    symbol: str
    bid: float
    ask: float
    mid: float
    timestamp: datetime


@dataclass(slots=True)
class ParsedMarket:
    strike_price: float | None
    condition_type: str | None
    expiry: datetime | None
    start_time: datetime | None
    open_reference_price: float | None
    resolution_source: str | None
    confidence: str
    notes: list[str]


@dataclass(slots=True)
class MarketSnapshot:
    captured_at: datetime
    market_id: str
    question: str
    slug: str | None
    start_time: datetime | None
    end_date: datetime | None
    seconds_since_start: float | None
    seconds_to_expiry: float | None
    strike_price: float | None
    open_reference_price: float | None
    condition_type: str | None
    binance_mid: float
    distance_to_strike: float | None
    distance_to_open: float | None
    distance_bps: float | None
    yes_bid: float | None
    yes_ask: float | None
    no_bid: float | None
    no_ask: float | None
    spread: float | None
    parser_confidence: str
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["captured_at"] = self.captured_at.isoformat()
        result["start_time"] = self.start_time.isoformat() if self.start_time else None
        result["end_date"] = self.end_date.isoformat() if self.end_date else None
        return result


@dataclass(slots=True)
class SignalEvaluation:
    fair_yes_probability: float | None
    edge_yes_buy: float | None
    edge_no_buy: float | None
    best_side: str
    gross_edge: float | None
    net_edge: float | None
    confidence: str
    should_alert: bool
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
