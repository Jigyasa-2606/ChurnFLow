from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row


def database_url() -> str:
    if url := os.environ.get("DATABASE_URL"):
        return url
    host = os.environ.get("POSTGRES_HOST", "postgres")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "churnflow")
    password = os.environ.get("POSTGRES_PASSWORD", "churnflow")
    db = os.environ.get("POSTGRES_DB", "churnflow")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def connect() -> psycopg.Connection:
    return psycopg.connect(database_url(), autocommit=True, row_factory=dict_row)


def fetch_active(conn: psycopg.Connection) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT model_version, training_time, features_version, auc, f1, logloss, promotion_status
            FROM model_versions
            WHERE promotion_status = 'active'
            LIMIT 1
            """
        )
        return cur.fetchone()


def list_models(conn: psycopg.Connection) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT model_version, training_time, features_version, auc, f1, logloss,
                   drift_triggered, promotion_status
            FROM model_versions
            ORDER BY training_time DESC
            """
        )
        return list(cur.fetchall())


def insert_prediction(
    conn: psycopg.Connection,
    *,
    customer_id: str,
    score: float,
    model_version: str,
    scoring_ts: datetime,
    latency_ms: float,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO predictions (customer_id, score, model_version, scoring_ts, latency_ms)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (customer_id, score, model_version, scoring_ts, latency_ms),
        )


def prediction_history(conn: psycopg.Connection, customer_id: str, limit: int = 20) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT score, model_version, scoring_ts, latency_ms
            FROM predictions
            WHERE customer_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (customer_id, limit),
        )
        return list(cur.fetchall())


def pipeline_stats(conn: psycopg.Connection) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) AS events, max(ts) AS last_event_ts FROM events")
        events = cur.fetchone() or {}
        cur.execute(
            """
            SELECT percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95_ms,
                   count(*) AS n
            FROM predictions
            WHERE created_at > NOW() - INTERVAL '5 minutes'
            """
        )
        latency = cur.fetchone() or {}
    return {
        "events": events.get("events"),
        "last_event_ts": events.get("last_event_ts"),
        "p95_ms": latency.get("p95_ms"),
        "predictions_5m": latency.get("n"),
    }


def latest_drift_by_kind(conn: psycopg.Connection) -> dict[str, dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT ON (kind)
                kind, psi, metrics, reference_id, created_at
            FROM drift_reports
            ORDER BY kind, created_at DESC
            """
        )
        rows = cur.fetchall()
    return {row["kind"]: row for row in rows}
