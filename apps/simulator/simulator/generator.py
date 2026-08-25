"""Synthetic shopper events for Churn Flow. Data source only — not a storefront."""

from __future__ import annotations

import os
import random
import uuid
from datetime import datetime, timezone
from typing import Any

EVENT_TYPES = (
    "page_view",
    "add_to_cart",
    "purchase",
    "session_end",
    "support_ticket",
)

CATEGORIES = ("electronics", "home", "fashion", "grocery", "beauty")

# Weighted toward browsing; purchases are less common.
EVENT_WEIGHTS = {
    "page_view": 0.50,
    "add_to_cart": 0.18,
    "purchase": 0.10,
    "session_end": 0.17,
    "support_ticket": 0.05,
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def customer_ids(count: int) -> list[str]:
    return [f"cust_{i:04d}" for i in range(1, count + 1)]


def _payload(event_type: str, session_id: str) -> dict[str, Any]:
    category = random.choice(CATEGORIES)
    if event_type == "purchase":
        return {
            "amount": round(random.uniform(8.0, 240.0), 2),
            "category": category,
            "session_id": session_id,
        }
    if event_type == "add_to_cart":
        return {"category": category, "session_id": session_id}
    if event_type == "page_view":
        return {"category": category, "session_id": session_id}
    if event_type == "session_end":
        return {"session_id": session_id}
    return {"session_id": session_id}


def make_event(
    customer_id: str,
    event_type: str | None = None,
    ts: datetime | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    chosen = event_type or random.choices(
        population=list(EVENT_WEIGHTS),
        weights=list(EVENT_WEIGHTS.values()),
        k=1,
    )[0]
    stamp = ts or utc_now()
    sid = session_id or str(uuid.uuid4())
    return {
        "event_id": f"evt_{uuid.uuid4().hex}",
        "customer_id": customer_id,
        "event_type": chosen,
        "ts": isoformat(stamp),
        "payload": _payload(chosen, sid),
    }


def env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def env_float(name: str, default: float) -> float:
    return float(os.environ.get(name, default))
