from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from statistics import pstdev
from urllib.error import URLError
from urllib.request import Request, urlopen
import json

from .config import Settings
from .models import BinanceTick


class BinanceClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.history: deque[tuple[datetime, float]] = deque(maxlen=settings.max_history_points)

    def fetch_mid(self) -> BinanceTick:
        url = f"https://api.binance.com/api/v3/ticker/bookTicker?symbol={self.settings.binance_symbol}"
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urlopen(request, timeout=self.settings.request_timeout_seconds) as response:
                payload = json.load(response)
        except URLError as exc:
            raise RuntimeError(f"Binance request failed: {exc}") from exc

        bid = float(payload["bidPrice"])
        ask = float(payload["askPrice"])
        mid = (bid + ask) / 2.0
        timestamp = datetime.now(timezone.utc)
        self.history.append((timestamp, mid))
        return BinanceTick(symbol=self.settings.binance_symbol, bid=bid, ask=ask, mid=mid, timestamp=timestamp)

    def realized_volatility(self) -> float | None:
        if len(self.history) < 10:
            return None

        prices = [price for _, price in self.history]
        mean_price = sum(prices) / len(prices)
        if mean_price <= 0:
            return None
        return pstdev(prices) / mean_price

    def first_price_at_or_after(self, target: datetime) -> float | None:
        for ts, price in self.history:
            if ts >= target:
                return price
        return None

    def latest_price(self) -> float | None:
        if not self.history:
            return None
        return self.history[-1][1]

    def seconds_covered(self) -> float:
        if len(self.history) < 2:
            return 0.0
        return (self.history[-1][0] - self.history[0][0]).total_seconds()
