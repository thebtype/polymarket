from __future__ import annotations

from datetime import datetime, timezone
from time import sleep


def log_status(message: str) -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] {message}", flush=True)

from .binance import BinanceClient
from .config import load_settings
from .discovery import MarketDiscovery
from .logger import EventLogger
from .model import estimate_fair_yes_probability
from .models import MarketSnapshot
from .parser import parse_market
from .polymarket import PolymarketClient
from .signals import evaluate_signal


def build_snapshot(market: dict, binance_mid: float, open_reference_price: float | None = None) -> MarketSnapshot:
    parsed = parse_market(market)
    captured_at = datetime.now(timezone.utc)
    end_date = parsed.expiry
    start_time = parsed.start_time
    seconds_since_start = None
    if start_time is not None:
        seconds_since_start = (captured_at - start_time).total_seconds()
    seconds_to_expiry = None
    if end_date is not None:
        seconds_to_expiry = (end_date - captured_at).total_seconds()

    yes_bid = PolymarketClient.parse_float(market.get("bestBid"))
    yes_ask = PolymarketClient.parse_float(market.get("bestAsk"))
    no_bid = None if yes_ask is None else max(0.0, 1.0 - yes_ask)
    no_ask = None if yes_bid is None else min(1.0, 1.0 - yes_bid)
    spread = None
    if yes_bid is not None and yes_ask is not None:
        spread = yes_ask - yes_bid

    effective_open_reference = open_reference_price if open_reference_price is not None else parsed.open_reference_price
    distance_to_strike = None
    distance_to_open = None
    distance_bps = None
    if parsed.strike_price is not None:
        distance_to_strike = parsed.strike_price - binance_mid
        distance_bps = (distance_to_strike / binance_mid) * 10000.0
    elif effective_open_reference is not None:
        distance_to_open = effective_open_reference - binance_mid
        distance_bps = (distance_to_open / binance_mid) * 10000.0

    return MarketSnapshot(
        captured_at=captured_at,
        market_id=str(market.get("id")),
        question=market.get("question") or "",
        slug=market.get("slug"),
        start_time=start_time,
        end_date=end_date,
        seconds_since_start=seconds_since_start,
        seconds_to_expiry=seconds_to_expiry,
        strike_price=parsed.strike_price,
        open_reference_price=effective_open_reference,
        condition_type=parsed.condition_type,
        binance_mid=binance_mid,
        distance_to_strike=distance_to_strike,
        distance_to_open=distance_to_open,
        distance_bps=distance_bps,
        yes_bid=yes_bid,
        yes_ask=yes_ask,
        no_bid=no_bid,
        no_ask=no_ask,
        spread=spread,
        parser_confidence=parsed.confidence,
        notes=parsed.notes,
    )


def _fmt(value: float | None, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def format_alert(snapshot: MarketSnapshot, signal) -> str:
    return (
        f"ALERT {signal.best_side.upper()} | {snapshot.question}\n"
        f"Binance mid: {_fmt(snapshot.binance_mid, 2)} | strike: {_fmt(snapshot.strike_price, 2)}\n"
        f"Time left: {_fmt(snapshot.seconds_to_expiry, 0)}s | spread: {_fmt(snapshot.spread)}\n"
        f"YES bid/ask: {_fmt(snapshot.yes_bid)}/{_fmt(snapshot.yes_ask)} | NO bid/ask: {_fmt(snapshot.no_bid)}/{_fmt(snapshot.no_ask)}\n"
        f"Fair YES: {_fmt(signal.fair_yes_probability)} | net edge: {_fmt(signal.net_edge)} | confidence: {signal.confidence}"
    )


def run() -> None:
    settings = load_settings()
    binance = BinanceClient(settings)
    polymarket = PolymarketClient(settings)
    discovery = MarketDiscovery(settings)
    logger = EventLogger(settings)
    current_event_slug = settings.event_slug

    log_status("gap bot started")
    while True:
        try:
            if not current_event_slug:
                current_event_slug = discovery.find_latest_event_slug()
                if current_event_slug:
                    log_status(f"tracking event slug: {current_event_slug}")
                else:
                    log_status("no active BTC 5m event slug found")
            settings.event_slug = current_event_slug

            tick = binance.fetch_mid()
            realized_vol = binance.realized_volatility()
            markets = polymarket.fetch_candidate_markets()

            if not markets:
                log_status("no candidate markets returned, retrying")
                current_event_slug = None
                sleep(settings.poll_interval_seconds)
                continue

            for market in markets:
                parsed = parse_market(market)
                if parsed.expiry is not None and parsed.expiry <= tick.timestamp:
                    log_status(f"market expired: {market.get('slug')}")
                    current_event_slug = None
                open_reference_price = None
                if parsed.condition_type == "range_close_vs_open" and parsed.start_time is not None:
                    open_reference_price = binance.first_price_at_or_after(parsed.start_time)
                snapshot = build_snapshot(market, tick.mid, open_reference_price=open_reference_price)
                fair_yes_probability = estimate_fair_yes_probability(snapshot, realized_vol)
                signal = evaluate_signal(snapshot, fair_yes_probability, settings)
                logger.log_snapshot(snapshot, signal)
                if signal.gross_edge is not None and signal.gross_edge > 0:
                    logger.log_signal(snapshot, signal)
                fair_text = _fmt(fair_yes_probability)
                open_text = _fmt(snapshot.open_reference_price, 2)
                edge_text = _fmt(signal.net_edge)
                ttl_text = _fmt(snapshot.seconds_to_expiry, 0)
                log_status(
                    f"slug={snapshot.slug} ttl={ttl_text}s mid={snapshot.binance_mid:.2f} open={open_text} "
                    f"fair_yes={fair_text} side={signal.best_side} net_edge={edge_text} alert={signal.should_alert}"
                )
                if signal.should_alert:
                    print(format_alert(snapshot, signal), flush=True)

            sleep(settings.poll_interval_seconds)
        except Exception as exc:
            log_status(f"error: {exc}")
            sleep(settings.poll_interval_seconds)


if __name__ == "__main__":
    run()
