from __future__ import annotations

from datetime import datetime, timezone
from html import unescape
import re
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json

from .config import Settings
from .time_utils import parse_iso8601


class PolymarketClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def fetch_candidate_markets(self) -> list[dict]:
        if self.settings.event_slug:
            markets = self.fetch_event_markets(self.settings.event_slug)
            if markets:
                return markets

        params = urlencode(
            {
                "limit": self.settings.market_query_limit,
                "active": "true",
                "closed": "false",
            }
        )
        url = f"{self.settings.gamma_base_url}/markets?{params}"
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urlopen(request, timeout=self.settings.request_timeout_seconds) as response:
                payload = json.load(response)
        except URLError as exc:
            raise RuntimeError(f"Polymarket request failed: {exc}") from exc

        return [market for market in payload if self._looks_relevant(market)]

    def fetch_event_markets(self, event_slug: str) -> list[dict]:
        url = f"https://polymarket.com/event/{event_slug}"
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urlopen(request, timeout=self.settings.request_timeout_seconds) as response:
                html = response.read().decode("utf-8", "ignore")
        except URLError as exc:
            raise RuntimeError(f"Polymarket event page request failed: {exc}") from exc

        match = re.search(r'"markets":(\[.*?\]),"series":', html)
        if not match:
            return []
        payload = json.loads(unescape(match.group(1)))
        return payload

    def _looks_relevant(self, market: dict) -> bool:
        haystack = " ".join(
            str(market.get(key, "")) for key in ("question", "description", "groupItemTitle")
        ).lower()
        return any(term in haystack for term in self.settings.market_search_terms)

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
