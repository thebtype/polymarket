from __future__ import annotations

from math import log, sqrt

from .math_utils import normal_cdf
from .models import MarketSnapshot


def estimate_fair_yes_probability(snapshot: MarketSnapshot, realized_vol: float | None) -> float | None:
    if snapshot.condition_type == "range_close_vs_open":
        if snapshot.seconds_to_expiry is None:
            return None
        if snapshot.open_reference_price is None or snapshot.open_reference_price <= 0:
            return None
        if snapshot.binance_mid <= 0:
            return None
        if realized_vol is None or realized_vol <= 0:
            realized_vol = 0.0015

        horizon = max(snapshot.seconds_to_expiry, 1.0)
        horizon_scale = sqrt(horizon / 300.0)
        sigma = max(realized_vol * horizon_scale, 1e-6)
        distance = log(snapshot.open_reference_price / snapshot.binance_mid)
        return 1.0 - normal_cdf(distance / sigma)

    if snapshot.strike_price is None or snapshot.seconds_to_expiry is None:
        return None
    if snapshot.strike_price <= 0 or snapshot.binance_mid <= 0:
        return None

    if realized_vol is None or realized_vol <= 0:
        realized_vol = 0.0015

    horizon = max(snapshot.seconds_to_expiry, 1.0)
    horizon_scale = sqrt(horizon / 300.0)
    sigma = max(realized_vol * horizon_scale, 1e-6)
    distance = log(snapshot.strike_price / snapshot.binance_mid)

    if snapshot.condition_type in {"above", "close_above", "touch"}:
        return 1.0 - normal_cdf(distance / sigma)
    if snapshot.condition_type in {"below", "close_below"}:
        return normal_cdf(distance / sigma)
    return None
