from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from churnflow_features.constants import (
    EVENT_ADD_TO_CART,
    EVENT_PAGE_VIEW,
    EVENT_PURCHASE,
    EVENT_SESSION_END,
    EVENT_SUPPORT_TICKET,
)
from churnflow_features.schema import Event, as_utc


def _amount(event: Event) -> float:
    raw = event.payload.get("amount", 0)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _category(event: Event) -> str | None:
    value = event.payload.get("category")
    if value is None or value == "":
        return None
    return str(value)


def _in_last_days(event: Event, t: datetime, days: int) -> bool:
    return (t - timedelta(days=days)) <= event.ts <= t


def _recency_days(events: Iterable[Event], t: datetime, types: set[str]) -> float:
    matching = [event.ts for event in events if event.event_type in types]
    if not matching:
        return 90.0
    last = max(matching)
    return max(0.0, (t - last).total_seconds() / 86400.0)


def summarize(events: list[Event], observation_time: datetime) -> dict[str, float]:
    t = as_utc(observation_time)
    purchases = [e for e in events if e.event_type == EVENT_PURCHASE]
    carts = [e for e in events if e.event_type == EVENT_ADD_TO_CART]
    tickets = [e for e in events if e.event_type == EVENT_SUPPORT_TICKET]
    sessions = [e for e in events if e.event_type == EVENT_SESSION_END]

    def purchase_count(days: int) -> float:
        return float(sum(1 for e in purchases if _in_last_days(e, t, days)))

    def monetary(days: int) -> float:
        return float(sum(_amount(e) for e in purchases if _in_last_days(e, t, days)))

    def session_count(days: int) -> float:
        return float(sum(1 for e in sessions if _in_last_days(e, t, days)))

    cart_n = len(carts)
    purchase_n = len(purchases)
    if cart_n == 0:
        cart_abandon_rate = 0.0
    else:
        converted = min(purchase_n / cart_n, 1.0)
        cart_abandon_rate = 1.0 - converted

    categories = {_category(e) for e in purchases if _category(e) is not None}

    return {
        "recency_days_last_purchase": _recency_days(events, t, {EVENT_PURCHASE}),
        "recency_days_last_session": _recency_days(
            events, t, {EVENT_SESSION_END, EVENT_PAGE_VIEW}
        ),
        "frequency_7d": purchase_count(7),
        "frequency_30d": purchase_count(30),
        "frequency_90d": purchase_count(90),
        "monetary_7d": monetary(7),
        "monetary_30d": monetary(30),
        "monetary_90d": monetary(90),
        "sessions_7d": session_count(7),
        "sessions_30d": session_count(30),
        "sessions_90d": session_count(90),
        "cart_abandon_rate": cart_abandon_rate,
        "support_tickets_30d": float(sum(1 for e in tickets if _in_last_days(e, t, 30))),
        "support_tickets_90d": float(len(tickets)),
        "category_diversity_90d": float(len(categories)),
    }
