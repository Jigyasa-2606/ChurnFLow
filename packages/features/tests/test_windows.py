from datetime import datetime, timezone

from churnflow_features.schema import Event
from churnflow_features.windows import events_at_or_before, events_in_feature_window


def _purchase(event_id: str, hour: int, amount: float) -> Event:
    return Event(
        event_id=event_id,
        customer_id="cust_42",
        event_type="purchase",
        ts=datetime(2026, 8, 25, hour, 0, 0, tzinfo=timezone.utc),
        payload={"amount": amount, "category": "electronics"},
    )


def test_events_at_or_before_keeps_equal_t_drops_after() -> None:
    events = [
        _purchase("a", 10, 10),
        _purchase("b", 11, 20),
        _purchase("c", 12, 30),
    ]
    t = datetime(2026, 8, 25, 11, 0, 0, tzinfo=timezone.utc)
    kept = events_at_or_before(events, t)
    assert [e.event_id for e in kept] == ["a", "b"]


def test_feature_window_drops_events_older_than_90_days() -> None:
    old = Event(
        event_id="old",
        customer_id="cust_42",
        event_type="purchase",
        ts=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        payload={"amount": 99},
    )
    recent = _purchase("new", 11, 20)
    t = datetime(2026, 8, 25, 11, 0, 0, tzinfo=timezone.utc)
    kept = events_in_feature_window([old, recent], t)
    assert [e.event_id for e in kept] == ["new"]
