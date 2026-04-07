from __future__ import annotations

from .config import Settings
from .models import MarketSnapshot, SignalEvaluation


def evaluate_signal(snapshot: MarketSnapshot, fair_yes_probability: float | None, settings: Settings) -> SignalEvaluation:
    reasons: list[str] = []
    if fair_yes_probability is None:
        reasons.append("missing fair probability")
    if snapshot.seconds_to_expiry is None or snapshot.seconds_to_expiry < settings.min_seconds_to_expiry:
        reasons.append("too close to expiry")
    if snapshot.spread is None or snapshot.spread > settings.max_spread:
        reasons.append("spread too wide")
    if snapshot.parser_confidence == "low":
        reasons.append("market parser confidence low")

    edge_yes = None
    edge_no = None
    if fair_yes_probability is not None and snapshot.yes_ask is not None:
        edge_yes = fair_yes_probability - snapshot.yes_ask
    if fair_yes_probability is not None and snapshot.no_ask is not None:
        edge_no = (1.0 - fair_yes_probability) - snapshot.no_ask

    best_side = "pass"
    gross_edge = None
    if edge_yes is not None or edge_no is not None:
        edge_yes_val = edge_yes if edge_yes is not None else float("-inf")
        edge_no_val = edge_no if edge_no is not None else float("-inf")
        if edge_yes_val >= edge_no_val:
            best_side = "yes"
            gross_edge = edge_yes
        else:
            best_side = "no"
            gross_edge = edge_no

    total_cost_buffer = settings.fee_buffer + settings.slippage_buffer + settings.safety_buffer
    net_edge = gross_edge - total_cost_buffer if gross_edge is not None else None

    should_alert = (
        not reasons
        and gross_edge is not None
        and gross_edge >= settings.min_gross_edge
        and net_edge is not None
        and net_edge >= settings.min_net_edge
    )

    confidence = "low"
    if should_alert and (net_edge or 0) >= settings.min_net_edge + 0.02:
        confidence = "high"
    elif should_alert:
        confidence = "medium"
    elif snapshot.parser_confidence == "high" and gross_edge is not None and gross_edge > 0:
        confidence = "medium"

    return SignalEvaluation(
        fair_yes_probability=fair_yes_probability,
        edge_yes_buy=edge_yes,
        edge_no_buy=edge_no,
        best_side=best_side,
        gross_edge=gross_edge,
        net_edge=net_edge,
        confidence=confidence,
        should_alert=should_alert,
        reasons=reasons,
    )
