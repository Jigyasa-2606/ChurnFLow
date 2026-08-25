from datetime import datetime, timezone

from churnflow_features import FEATURES_VERSION, build_features


def test_build_features_accepts_raw_dicts() -> None:
    t = datetime(2026, 8, 25, 15, 0, 0, tzinfo=timezone.utc)
    events = [
        {
            "event_id": "evt_1",
            "customer_id": "cust_42",
            "event_type": "add_to_cart",
            "ts": "2026-08-25T14:00:00Z",
            "payload": {"category": "electronics"},
        },
        {
            "event_id": "evt_2",
            "customer_id": "cust_42",
            "event_type": "purchase",
            "ts": "2026-08-25T14:30:00Z",
            "payload": {"amount": 1499, "category": "electronics"},
        },
        {
            "event_id": "evt_3",
            "customer_id": "cust_42",
            "event_type": "support_ticket",
            "ts": "2026-08-25T14:45:00Z",
            "payload": {},
        },
    ]
    features = build_features(events, observation_time=t)
    assert features["frequency_7d"] == 1.0
    assert features["monetary_7d"] == 1499.0
    assert features["cart_abandon_rate"] == 0.0
    assert features["support_tickets_30d"] == 1.0
    assert features["category_diversity_90d"] == 1.0
    assert FEATURES_VERSION == "v1"
