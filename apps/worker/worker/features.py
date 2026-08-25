from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import redis

from churnflow_features import FEATURES_VERSION, LOOKBACK_DAYS, build_features
from worker.db import fetch_events_for_features, upsert_snapshot


def redis_url() -> str:
    return os.environ.get("REDIS_URL", "redis://redis:6379/0")


def connect_redis() -> redis.Redis:
    return redis.Redis.from_url(redis_url(), decode_responses=True)


def features_key(customer_id: str) -> str:
    return f"features:{customer_id}"


def write_redis_features(
    client: redis.Redis,
    customer_id: str,
    features: dict[str, float],
    observation_time: datetime,
) -> None:
    mapping = {name: f"{value:.6g}" for name, value in features.items()}
    mapping["_observation_time"] = observation_time.isoformat()
    mapping["_features_version"] = FEATURES_VERSION
    client.hset(features_key(customer_id), mapping=mapping)


def refresh_customer_features(
    conn: Any,
    redis_client: redis.Redis,
    customer_id: str,
    observation_time: datetime,
) -> dict[str, float]:
    """Rebuild features at observation T from Postgres (event.ts <= T) and cache in Redis.

    Recompute-from-source is idempotent: a Kafka redelivery cannot double-count a purchase.
    """
    events = fetch_events_for_features(conn, customer_id, observation_time, LOOKBACK_DAYS)
    features = build_features(events, observation_time=observation_time)
    write_redis_features(redis_client, customer_id, features, observation_time)
    upsert_snapshot(conn, customer_id, observation_time, FEATURES_VERSION, features)
    return features
