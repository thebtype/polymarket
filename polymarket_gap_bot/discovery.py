from __future__ import annotations

from datetime import datetime, timezone
import json
from urllib.request import Request, urlopen

from .config import Settings


class MarketDiscovery:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def find_latest_event_slug(self) -> str | None:
        candidates = self._load_series_catalog()
        now = datetime.now(timezone.utc)
        best_slug = None
        best_end = None

        for item in candidates:
            slug = item.get("slug")
            if not slug:
                continue
            if not slug.startswith("btc-updown-5m-"):
                continue
            end_date = self._parse_datetime(item.get("endDate") or item.get("end_date"))
            if end_date is None:
                continue
            if end_date < now:
                continue
            if best_end is None or end_date < best_end:
                best_end = end_date
                best_slug = slug

        return best_slug

    def _load_series_catalog(self) -> list[dict]:
        rows: list[dict] = []
        for offset in range(0, self.settings.series_search_limit, 200):
            url = f"{self.settings.gamma_base_url}/series?limit=200&offset={offset}"
            request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(request, timeout=self.settings.request_timeout_seconds) as response:
                payload = json.load(response)
            for item in payload:
                if item.get("slug") == self.settings.series_slug:
                    rows.extend(item.get("events") or [])
                    return rows
        return rows

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            return None
