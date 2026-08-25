from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

from trainer.promote import Metrics


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
    return psycopg.connect(database_url(), autocommit=False, row_factory=dict_row)


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


def active_metrics(row: dict[str, Any] | None) -> Metrics | None:
    if row is None:
        return None
    return Metrics(auc=float(row["auc"]), f1=float(row["f1"]), logloss=float(row["logloss"]))


def insert_version(
    conn: psycopg.Connection,
    *,
    model_version: str,
    features_version: str,
    metrics: Metrics,
    drift_triggered: bool,
    promotion_status: str,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO model_versions (
                model_version, training_time, features_version,
                auc, f1, logloss, drift_triggered, promotion_status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                model_version,
                datetime.now(timezone.utc),
                features_version,
                metrics.auc,
                metrics.f1,
                metrics.logloss,
                drift_triggered,
                promotion_status,
            ),
        )
    conn.commit()


def promote_version(conn: psycopg.Connection, model_version: str) -> None:
    """Demote current active to shadow, then mark candidate active (unique active index)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE model_versions
            SET promotion_status = 'shadow'
            WHERE promotion_status = 'active'
            """
        )
        cur.execute(
            """
            UPDATE model_versions
            SET promotion_status = 'active'
            WHERE model_version = %s
            """,
            (model_version,),
        )
    conn.commit()


def insert_drift_report(
    conn: psycopg.Connection,
    *,
    kind: str,
    psi: float | None,
    metrics: dict[str, Any],
    reference_id: str,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO drift_reports (kind, psi, metrics, reference_id)
            VALUES (%s, %s, %s, %s)
            """,
            (kind, psi, Json(metrics), reference_id),
        )
    conn.commit()


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
