from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from worker.db import FETCH_EVENTS_SQL
from worker.features import features_key, refresh_customer_features, write_redis_features


def test_fetch_sql_is_bounded_by_observation_time() -> None:
    assert "ts <= %s" in FETCH_EVENTS_SQL
    assert "customer_id = %s" in FETCH_EVENTS_SQL


def test_features_key_matches_data_model() -> None:
    assert features_key("cust_0042") == "features:cust_0042"


def test_write_redis_features_stores_hash_and_version() -> None:
    client = MagicMock()
    t = datetime(2026, 8, 25, 11, 0, 0, tzinfo=timezone.utc)
    write_redis_features(client, "cust_0042", {"frequency_90d": 2.0}, t)
    client.hset.assert_called_once()
    key, kwargs = client.hset.call_args[0][0], client.hset.call_args[1]
    assert key == "features:cust_0042"
    assert kwargs["mapping"]["frequency_90d"] == "2"
    assert kwargs["mapping"]["_features_version"] == "v1"
    assert "2026-08-25T11:00:00" in kwargs["mapping"]["_observation_time"]


def test_refresh_rebuilds_from_fetched_rows_not_raw_kafka_payload() -> None:
    """A redelivered purchase cannot be counted twice if Postgres already has one row."""
    t = datetime(2026, 8, 25, 11, 0, 0, tzinfo=timezone.utc)
    rows = [
        {
            "event_id": "evt_10",
            "customer_id": "cust_42",
            "event_type": "purchase",
            "ts": datetime(2026, 8, 25, 10, 0, 0, tzinfo=timezone.utc),
            "payload": {"amount": 10, "category": "electronics"},
        },
        {
            "event_id": "evt_11",
            "customer_id": "cust_42",
            "event_type": "purchase",
            "ts": t,
            "payload": {"amount": 20, "category": "electronics"},
        },
    ]
    conn = MagicMock()
    redis_client = MagicMock()
    with (
        patch("worker.features.fetch_events_for_features", return_value=rows) as fetch,
        patch("worker.features.upsert_snapshot") as snapshot,
    ):
        features = refresh_customer_features(conn, redis_client, "cust_42", t)

    fetch.assert_called_once_with(conn, "cust_42", t, 90)
    assert features["frequency_90d"] == 2.0
    assert features["monetary_90d"] == 30.0
    redis_client.hset.assert_called_once()
    snapshot.assert_called_once()
    assert snapshot.call_args[0][3] == "v1"
