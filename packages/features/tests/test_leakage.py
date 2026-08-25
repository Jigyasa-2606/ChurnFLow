"""Leakage tests: features and labels must not use the wrong side of T."""

from datetime import datetime, timedelta, timezone

from churnflow_features import build_features, churn_label
from churnflow_features.schema import Event


def _purchase(event_id: str, ts: datetime, amount: float) -> Event:
    return Event(
        event_id=event_id,
        customer_id="cust_42",
        event_type="purchase",
        ts=ts,
        payload={"amount": amount, "category": "electronics"},
    )


def test_future_purchase_must_not_enter_features() -> None:
    """Purchases at 10:00 and 11:00 may be used at T=11:00. 12:00 must not."""
    t = datetime(2026, 8, 25, 11, 0, 0, tzinfo=timezone.utc)
    events = [
        _purchase("evt_10", t - timedelta(hours=1), 10),
        _purchase("evt_11", t, 20),
        _purchase("evt_12", t + timedelta(hours=1), 1000),
    ]

    features = build_features(events, observation_time=t)

    assert features["frequency_90d"] == 2.0
    assert features["monetary_90d"] == 30.0
    assert features["monetary_90d"] != 1030.0


def test_same_events_with_later_t_do_include_noon_purchase() -> None:
    t_noon = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
    eleven = datetime(2026, 8, 25, 11, 0, 0, tzinfo=timezone.utc)
    events = [
        _purchase("evt_10", eleven - timedelta(hours=1), 10),
        _purchase("evt_11", eleven, 20),
        _purchase("evt_12", t_noon, 1000),
    ]
    features = build_features(events, observation_time=t_noon)
    assert features["frequency_90d"] == 3.0
    assert features["monetary_90d"] == 1030.0


def test_purchase_at_t_does_not_count_as_retained_label() -> None:
    t = datetime(2026, 8, 25, 11, 0, 0, tzinfo=timezone.utc)
    events = [_purchase("at_t", t, 50)]
    assert churn_label(events, observation_time=t) == 1


def test_purchase_strictly_after_t_within_horizon_is_retained() -> None:
    t = datetime(2026, 8, 25, 11, 0, 0, tzinfo=timezone.utc)
    events = [_purchase("after", t + timedelta(days=1), 50)]
    assert churn_label(events, observation_time=t) == 0


def test_purchase_after_label_horizon_does_not_count() -> None:
    t = datetime(2026, 8, 25, 11, 0, 0, tzinfo=timezone.utc)
    events = [_purchase("too_late", t + timedelta(days=15), 50)]
    assert churn_label(events, observation_time=t) == 1
