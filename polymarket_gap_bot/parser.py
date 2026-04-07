from __future__ import annotations

from datetime import datetime
import re

from .models import ParsedMarket
from .polymarket import PolymarketClient
from .time_utils import parse_iso8601

TIME_RANGE_PATTERN = re.compile(
    r"(?P<month>[A-Za-z]+)\s+(?P<day>\d+),\s+(?P<start>\d{1,2}:\d{2}(?:AM|PM))-(?P<end>\d{1,2}:\d{2}(?:AM|PM))\s+ET",
    re.IGNORECASE,
)

STRIKE_PATTERNS = [
    re.compile(r"(?:above|over|greater than)\s*\$?([\d,]+(?:\.\d+)?(?:[mk])?)", re.IGNORECASE),
    re.compile(r"(?:below|under|less than)\s*\$?([\d,]+(?:\.\d+)?(?:[mk])?)", re.IGNORECASE),
    re.compile(r"hit\s*\$?([\d,]+(?:\.\d+)?(?:[mk])?)", re.IGNORECASE),
]


def _parse_numeric_token(token: str) -> float:
    cleaned = token.replace(",", "").strip().lower()
    multiplier = 1.0
    if cleaned.endswith("k"):
        multiplier = 1_000.0
        cleaned = cleaned[:-1]
    elif cleaned.endswith("m"):
        multiplier = 1_000_000.0
        cleaned = cleaned[:-1]
    return float(cleaned) * multiplier


def _parse_updown_market(question: str) -> tuple[str | None, list[str]]:
    notes: list[str] = []
    if "up or down" not in question.lower():
        return None, notes
    if TIME_RANGE_PATTERN.search(question):
        return "range_close_vs_open", notes
    notes.append("Up/down market detected but could not parse time window")
    return "range_close_vs_open", notes


def parse_market(market: dict) -> ParsedMarket:
    question = market.get("question") or ""
    description = market.get("description") or ""
    text = f"{question}\n{description}"
    lower = text.lower()

    notes: list[str] = []
    condition_type, extra_notes = _parse_updown_market(question)
    notes.extend(extra_notes)
    if condition_type == "range_close_vs_open":
        pass
    elif "close above" in lower or "end above" in lower:
        condition_type = "close_above"
    elif "close below" in lower or "end below" in lower:
        condition_type = "close_below"
    elif "above" in lower or "over" in lower:
        condition_type = "above"
    elif "below" in lower or "under" in lower:
        condition_type = "below"
    elif "hit" in lower or "touch" in lower:
        condition_type = "touch"
    else:
        notes.append("Could not infer condition type from question/description")

    strike_price = None
    for pattern in STRIKE_PATTERNS:
        match = pattern.search(text)
        if match:
            strike_price = _parse_numeric_token(match.group(1))
            break
    if strike_price is None and condition_type != "range_close_vs_open":
        notes.append("Could not parse strike price")

    start_time = parse_iso8601(market.get("eventStartTime") or market.get("startDate"))
    expiry = PolymarketClient.parse_datetime(market.get("endDate") or market.get("endDateIso") or market.get("end_date"))
    if expiry is None:
        notes.append("Missing or invalid expiry")

    open_reference_price = None
    resolution_source = market.get("resolutionSource") or market.get("resolution_source") or None
    if not resolution_source and "binance" in lower:
        resolution_source = "Binance"

    confidence = "high"
    if len(notes) == 1:
        confidence = "medium"
    elif len(notes) >= 2:
        confidence = "low"

    return ParsedMarket(
        strike_price=strike_price,
        condition_type=condition_type,
        expiry=expiry,
        start_time=start_time,
        open_reference_price=open_reference_price,
        resolution_source=resolution_source,
        confidence=confidence,
        notes=notes,
    )
