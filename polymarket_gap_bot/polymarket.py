from __future__ import annotations

from datetime import datetime, timezone
from html import unescape
from urllib.error import URLError
from urllib.request import Request, urlopen
import json

from .config import Settings
from .time_utils import parse_iso8601


class PolymarketClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def fetch_candidate_markets(self) -> list[dict]:
        if self.settings.event_slug:
            return self.fetch_event_markets(self.settings.event_slug)
        return []

    def fetch_event_markets(self, event_slug: str) -> list[dict]:
        url = f"https://polymarket.com/event/{event_slug}"
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urlopen(request, timeout=self.settings.request_timeout_seconds) as response:
                html = response.read().decode("utf-8", "ignore")
        except URLError as exc:
            raise RuntimeError(f"Polymarket event page request failed: {exc}") from exc

        marker = '"markets":'
        start = html.find(marker)
        if start == -1:
            return []
        start = html.find('[', start)
        if start == -1:
            return []

        depth = 0
        end = None
        for idx in range(start, len(html)):
            char = html[idx]
            if char == '[':
                depth += 1
            elif char == ']':
                depth -= 1
                if depth == 0:
                    end = idx + 1
                    break

        if end is None:
            return []

        payload = json.loads(unescape(html[start:end]))
        return [market for market in payload if self._looks_like_btc_5m_market(market)]

    def _looks_like_btc_5m_market(self, market: dict) -> bool:
        haystack = " ".join(
            str(market.get(key, "")) for key in ("question", "description", "groupItemTitle", "slug")
        ).lower()
        btc_terms = ("bitcoin", "btc")
        updown_terms = ("up or down", "up/down", "updown")
        short_window_terms = ("5m", "5 minute", "5-minute")
        return (
            any(term in haystack for term in btc_terms)
            and any(term in haystack for term in updown_terms)
            and any(term in haystack for term in short_window_terms)
        )

    @staticmethod
    def parse_datetime(value: str | None) -> datetime | None:
        return parse_iso8601(value)

    @staticmethod
    def parse_float(value: str | float | int | None) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
