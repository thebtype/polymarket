from __future__ import annotations

from math import erf, sqrt


def normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + erf(value / sqrt(2.0)))
