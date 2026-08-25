"""Synthetic histories with a real observation date T.

Live Kafka events are too recent for a 14-day label. Training uses dated histories
so features see only event.ts <= T and labels see purchases strictly after T.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import numpy as np

from churnflow_features import LOOKBACK_DAYS, build_features, churn_label
from churnflow_features.schema import parse_events

CATEGORIES = ("electronics", "home", "fashion", "grocery", "beauty")
DEFAULT_T = datetime(2026, 7, 1, 0, 0, 0, tzinfo=timezone.utc)


def _event(customer_id: str, event_type: str, ts: datetime, payload: dict | None = None) -> dict:
    return {
        "event_id": f"evt_{uuid.uuid4().hex}",
        "customer_id": customer_id,
        "event_type": event_type,
        "ts": ts,
        "payload": payload or {},
    }


def _jitter(rng: np.random.Generator, start: datetime, end: datetime) -> datetime:
    span = max((end - start).total_seconds(), 1.0)
    return start + timedelta(seconds=float(rng.uniform(0, span)))


def generate_customer_events(
    rng: np.random.Generator,
    customer_id: str,
    observation_time: datetime,
    will_churn: bool,
) -> list[dict]:
    t = observation_time
    start = t - timedelta(days=LOOKBACK_DAYS)
    label_end = t + timedelta(days=14)
    events: list[dict] = []

    n_sessions = int(rng.integers(6, 16))
    n_purchases = int(rng.integers(0, 7) if will_churn else rng.integers(2, 10))
    if rng.random() < 0.22:
        n_purchases = int(rng.integers(1, 6))
    n_tickets = int(rng.integers(0, 4) if will_churn else rng.integers(0, 3))

    for _ in range(n_sessions):
        ts = _jitter(rng, start, t)
        sid = str(uuid.uuid4())
        cat = str(rng.choice(CATEGORIES))
        events.append(_event(customer_id, "page_view", ts, {"category": cat, "session_id": sid}))
        events.append(
            _event(
                customer_id,
                "session_end",
                min(ts + timedelta(minutes=int(rng.integers(5, 40))), t),
                {"session_id": sid},
            )
        )

    for _ in range(n_purchases):
        ts = _jitter(rng, start, t)
        cat = str(rng.choice(CATEGORIES))
        events.append(_event(customer_id, "add_to_cart", ts, {"category": cat}))
        events.append(
            _event(
                customer_id,
                "purchase",
                min(ts + timedelta(minutes=3), t),
                {"amount": float(rng.uniform(15, 180)), "category": cat},
            )
        )

    if will_churn:
        for _ in range(int(rng.integers(1, 4))):
            ts = _jitter(rng, start, t)
            events.append(_event(customer_id, "add_to_cart", ts, {"category": str(rng.choice(CATEGORIES))}))

    for _ in range(n_tickets):
        events.append(_event(customer_id, "support_ticket", _jitter(rng, start, t), {}))

    labeled_churn = will_churn
    if rng.random() < 0.12:
        labeled_churn = not will_churn

    if not labeled_churn:
        n_keep = int(rng.integers(1, 4))
        for _ in range(n_keep):
            ts = _jitter(rng, t + timedelta(seconds=1), label_end)
            cat = str(rng.choice(CATEGORIES))
            events.append(
                _event(
                    customer_id,
                    "purchase",
                    ts,
                    {"amount": float(rng.uniform(15, 180)), "category": cat},
                )
            )
    else:
        if rng.random() < 0.5:
            events.append(
                _event(
                    customer_id,
                    "page_view",
                    _jitter(rng, t + timedelta(seconds=1), label_end),
                    {"category": str(rng.choice(CATEGORIES))},
                )
            )

    return events


def build_matrix(
    n_samples: int,
    seed: int = 7,
    observation_time: datetime = DEFAULT_T,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    rng = np.random.default_rng(seed)
    rows: list[list[float]] = []
    labels: list[int] = []
    feature_names: list[str] | None = None

    for i in range(n_samples):
        customer_id = f"train_{i:05d}"
        will_churn = bool(rng.random() < 0.42)
        events = generate_customer_events(rng, customer_id, observation_time, will_churn)
        features = build_features(events, observation_time=observation_time)
        if feature_names is None:
            feature_names = sorted(features)
        rows.append([features[name] for name in feature_names])
        labels.append(churn_label(parse_events(events), observation_time))

    assert feature_names is not None
    return np.asarray(rows, dtype=np.float64), np.asarray(labels, dtype=np.int32), feature_names
