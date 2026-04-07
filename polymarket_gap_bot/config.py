from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os


@dataclass(slots=True)
class Settings:
    binance_symbol: str = os.getenv("BINANCE_SYMBOL", "BTCUSDT")
    gamma_base_url: str = os.getenv("GAMMA_BASE_URL", "https://gamma-api.polymarket.com")
    poll_interval_seconds: float = float(os.getenv("POLL_INTERVAL_SECONDS", "5"))
    binance_stale_after_seconds: float = float(os.getenv("BINANCE_STALE_AFTER_SECONDS", "2.0"))
    polymarket_stale_after_seconds: float = float(os.getenv("POLYMARKET_STALE_AFTER_SECONDS", "5.0"))
    min_seconds_to_expiry: int = int(os.getenv("MIN_SECONDS_TO_EXPIRY", "30"))
    max_spread: float = float(os.getenv("MAX_SPREAD", "0.05"))
    min_gross_edge: float = float(os.getenv("MIN_GROSS_EDGE", "0.05"))
    min_net_edge: float = float(os.getenv("MIN_NET_EDGE", "0.03"))
    fee_buffer: float = float(os.getenv("FEE_BUFFER", "0.01"))
    slippage_buffer: float = float(os.getenv("SLIPPAGE_BUFFER", "0.01"))
    safety_buffer: float = float(os.getenv("SAFETY_BUFFER", "0.005"))
    volatility_lookback_seconds: int = int(os.getenv("VOL_LOOKBACK_SECONDS", "300"))
    max_history_points: int = int(os.getenv("MAX_HISTORY_POINTS", "600"))
    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))
    market_query_limit: int = int(os.getenv("MARKET_QUERY_LIMIT", "200"))
    series_search_limit: int = int(os.getenv("SERIES_SEARCH_LIMIT", "1600"))
    event_slug: str | None = os.getenv("POLYMARKET_EVENT_SLUG") or None
    series_slug: str = os.getenv("POLYMARKET_SERIES_SLUG", "btc-up-or-down-5m")
    market_search_terms: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            term.strip().lower()
            for term in os.getenv(
                "MARKET_SEARCH_TERMS",
                "bitcoin,btc,5m,5 minute,5-minute,binance",
            ).split(",")
            if term.strip()
        )
    )
    data_dir: Path = Path(os.getenv("DATA_DIR", "data"))

    @property
    def snapshots_path(self) -> Path:
        return self.data_dir / "market_snapshots.jsonl"

    @property
    def signals_path(self) -> Path:
        return self.data_dir / "signals.csv"


def load_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
