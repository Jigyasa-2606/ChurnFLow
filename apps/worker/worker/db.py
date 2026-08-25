from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg
from psycopg.types.json import Json

INSERT_EVENT_SQL = """
INSERT INTO events (event_id, customer_id, event_type, ts, payload)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (event_id) DO NOTHING
"""

FETCH_EVENTS_SQL = """
SELECT event_id, customer_id, event_type, ts, payload
FROM events
WHERE customer_id = %s
  AND ts <= %s
  AND ts >= %s
ORDER BY ts ASC
"""

UPSERT_SNAPSHOT_SQL = """
INSERT INTO feature_snapshots (customer_id, observation_time, features_version, features)
VALUES (%s, %s, %s, %s)
ON CONFLICT (customer_id, observation_time, features_version)
DO UPDATE SET features = EXCLUDED.features
"""

REQUIRED_FIELDS = ("event_id", "customer_id", "event_type", "ts")


def database_url() -> str:
    if url := os.environ.get("DATABASE_URL"):
        return url
    host = os.environ.get("POSTGRES_HOST", "postgres")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "churnflow")
    password = os.environ.get("POSTGRES_PASSWORD", "churnflow")
    db = os.environ.get("POSTGRES_DB", "churnflow")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def parse_ts(value: Any) -> datetime:
    if isinstance(value, datetime):
        ts = value
    else:
        text = str(value).replace("Z", "+00:00")
        ts = datetime.fromisoformat(text)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def validate_event(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("event must be an object")
    missing = [field for field in REQUIRED_FIELDS if not raw.get(field)]
    if missing:
        raise ValueError(f"missing fields: {missing}")
    payload = raw.get("payload") or {}
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    return {
        "event_id": str(raw["event_id"]),
        "customer_id": str(raw["customer_id"]),
        "event_type": str(raw["event_type"]),
        "ts": parse_ts(raw["ts"]),
        "payload": payload,
    }


def connect() -> psycopg.Connection:
    return psycopg.connect(database_url(), autocommit=False)


def upsert_event(conn: psycopg.Connection, event: dict[str, Any]) -> bool:
    """Insert event. Returns True if a new row was written, False on duplicate event_id."""
    with conn.cursor() as cur:
        cur.execute(
            INSERT_EVENT_SQL,
            (
                event["event_id"],
                event["customer_id"],
                event["event_type"],
                event["ts"],
                Json(event["payload"]),
            ),
        )
        inserted = cur.rowcount == 1
    conn.commit()
    return inserted


def fetch_events_for_features(
    conn: psycopg.Connection,
    customer_id: str,
    observation_time: datetime,
    lookback_days: int,
) -> list[dict[str, Any]]:
    """Load events for customer_id with event.ts <= T (and within lookback)."""
    start = parse_ts(observation_time) - timedelta(days=lookback_days)
    with conn.cursor() as cur:
        cur.execute(FETCH_EVENTS_SQL, (customer_id, observation_time, start))
        rows = cur.fetchall()
    events: list[dict[str, Any]] = []
    for event_id, cid, event_type, ts, payload in rows:
        events.append(
            {
                "event_id": event_id,
                "customer_id": cid,
                "event_type": event_type,
                "ts": parse_ts(ts),
                "payload": payload if isinstance(payload, dict) else {},
            }
        )
    return events


def upsert_snapshot(
    conn: psycopg.Connection,
    customer_id: str,
    observation_time: datetime,
    features_version: str,
    features: dict[str, float],
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            UPSERT_SNAPSHOT_SQL,
            (customer_id, observation_time, features_version, Json(features)),
        )
    conn.commit()


def decode_message(value: bytes | None) -> dict[str, Any]:
    if not value:
        raise ValueError("empty kafka payload")
    return validate_event(json.loads(value.decode("utf-8")))
