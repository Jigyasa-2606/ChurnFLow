from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from worker.db import decode_message, upsert_event, validate_event


def test_validate_event_parses_iso_ts() -> None:
    event = validate_event(
        {
            "event_id": "evt_1",
            "customer_id": "cust_42",
            "event_type": "purchase",
            "ts": "2026-08-25T15:20:10Z",
            "payload": {"amount": 1499},
        }
    )
    assert event["event_id"] == "evt_1"
    assert event["ts"] == datetime(2026, 8, 25, 15, 20, 10, tzinfo=timezone.utc)
    assert event["payload"]["amount"] == 1499


def test_validate_event_rejects_missing_event_id() -> None:
    with pytest.raises(ValueError, match="missing fields"):
        validate_event(
            {
                "customer_id": "cust_42",
                "event_type": "purchase",
                "ts": "2026-08-25T15:20:10Z",
            }
        )


def test_decode_message_roundtrip() -> None:
    raw = (
        b'{"event_id":"evt_9","customer_id":"cust_1","event_type":"page_view",'
        b'"ts":"2026-08-25T15:20:10Z","payload":{}}'
    )
    event = decode_message(raw)
    assert event["event_id"] == "evt_9"


def test_upsert_event_returns_true_when_row_inserted() -> None:
    conn = MagicMock()
    cur = MagicMock()
    cur.rowcount = 1
    conn.cursor.return_value.__enter__.return_value = cur

    inserted = upsert_event(
        conn,
        {
            "event_id": "evt_1",
            "customer_id": "cust_42",
            "event_type": "purchase",
            "ts": datetime(2026, 8, 25, 15, 20, 10, tzinfo=timezone.utc),
            "payload": {"amount": 10},
        },
    )

    assert inserted is True
    conn.commit.assert_called_once()
    sql = cur.execute.call_args[0][0]
    assert "ON CONFLICT (event_id) DO NOTHING" in sql


def test_upsert_event_returns_false_on_duplicate_event_id() -> None:
    conn = MagicMock()
    cur = MagicMock()
    cur.rowcount = 0
    conn.cursor.return_value.__enter__.return_value = cur

    inserted = upsert_event(
        conn,
        {
            "event_id": "evt_1",
            "customer_id": "cust_42",
            "event_type": "purchase",
            "ts": datetime(2026, 8, 25, 15, 20, 10, tzinfo=timezone.utc),
            "payload": {},
        },
    )

    assert inserted is False
    conn.commit.assert_called_once()
