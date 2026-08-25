from __future__ import annotations

import json
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from typing import Any

import joblib
import redis
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable
from prometheus_client import Histogram
from prometheus_fastapi_instrumentator import Instrumentator
from psycopg import OperationalError

from api.db import (
    connect,
    fetch_active,
    insert_prediction,
    latest_drift_by_kind,
    list_models,
    pipeline_stats,
    prediction_history,
)
from api.scoring import (
    HIGH_RISK_THRESHOLD,
    artifact_paths,
    features_from_redis_hash,
    features_key,
    load_feature_names,
    score_key,
    utc_now,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("api")

PREDICT_LATENCY = Histogram(
    "churn_predict_latency_seconds",
    "Time from Redis features to model score",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0),
)

state: dict[str, Any] = {
    "model": None,
    "feature_names": [],
    "model_version": None,
    "redis": None,
    "db": None,
    "producer": None,
    "stop": threading.Event(),
}


def redis_client() -> redis.Redis:
    url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    return redis.Redis.from_url(url, decode_responses=True)


def load_active_model() -> None:
    db = state["db"]
    active = fetch_active(db)
    if active is None:
        raise RuntimeError("no active model in model_versions")
    version = active["model_version"]
    if version == state["model_version"] and state["model"] is not None:
        return
    model_path, _names_path = artifact_paths(version)
    if not model_path.exists():
        raise RuntimeError(f"artifact missing: {model_path}")
    state["model"] = joblib.load(model_path)
    state["feature_names"] = load_feature_names(version)
    state["model_version"] = version
    log.info("serving %s features=%s", version, state["feature_names"])


def connect_kafka() -> KafkaProducer | None:
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
    try:
        producer = KafkaProducer(
            bootstrap_servers=bootstrap.split(","),
            acks="all",
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
            key_serializer=lambda key: key.encode("utf-8"),
        )
        log.info("kafka producer ready %s", bootstrap)
        return producer
    except NoBrokersAvailable:
        log.warning("kafka unavailable; predictions will skip the bus")
        return None


def publish(topic: str, key: str, payload: dict[str, Any]) -> None:
    producer = state["producer"]
    if producer is None:
        return
    try:
        producer.send(topic, key=key, value=payload)
    except KafkaError:
        log.warning("kafka publish failed topic=%s", topic)


def score_customer(customer_id: str) -> dict[str, Any]:
    load_active_model()
    raw = state["redis"].hgetall(features_key(customer_id))
    if not raw:
        raise HTTPException(status_code=404, detail=f"no features for {customer_id}")
    vector, features, features_version = features_from_redis_hash(raw, state["feature_names"])
    started = time.perf_counter()
    score = float(state["model"].predict_proba(vector.reshape(1, -1))[0, 1])
    latency_s = time.perf_counter() - started
    PREDICT_LATENCY.observe(latency_s)
    latency_ms = latency_s * 1000.0
    scoring_ts = utc_now()
    version = state["model_version"]
    insert_prediction(
        state["db"],
        customer_id=customer_id,
        score=score,
        model_version=version,
        scoring_ts=scoring_ts,
        latency_ms=latency_ms,
    )
    state["redis"].hset(
        score_key(customer_id),
        mapping={
            "score": f"{score:.6g}",
            "model_version": version,
            "latency_ms": f"{latency_ms:.3f}",
            "scored_at": scoring_ts.isoformat(),
            "risk": "HIGH" if score >= HIGH_RISK_THRESHOLD else "LOW",
        },
    )
    payload = {
        "customer_id": customer_id,
        "score": score,
        "model_version": version,
        "ts": scoring_ts.isoformat(),
        "latency_ms": latency_ms,
    }
    publish("churn.predictions", customer_id, payload)
    if score >= HIGH_RISK_THRESHOLD:
        publish("churn.alerts", customer_id, payload)
    return {
        "customer_id": customer_id,
        "score": score,
        "risk": "HIGH" if score >= HIGH_RISK_THRESHOLD else "LOW",
        "model_version": version,
        "features_version": features_version,
        "latency_ms": round(latency_ms, 3),
        "features": features,
        "observation_time": raw.get("_observation_time"),
    }


def scorer_loop() -> None:
    interval = float(os.environ.get("SCORE_INTERVAL_SEC", "5"))
    while not state["stop"].wait(interval):
        try:
            load_active_model()
            keys = list(state["redis"].scan_iter(match="features:*", count=200))
            for key in keys:
                customer_id = key.split(":", 1)[1]
                try:
                    score_customer(customer_id)
                except HTTPException:
                    continue
                except Exception:
                    log.exception("score failed customer=%s", customer_id)
        except Exception:
            log.exception("scorer loop error")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    for attempt in range(1, 31):
        try:
            state["db"] = connect()
            state["redis"] = redis_client()
            state["redis"].ping()
            load_active_model()
            break
        except (OperationalError, RuntimeError, redis.RedisError) as exc:
            log.warning("api waiting for deps (attempt %s/30): %s", attempt, exc)
            time.sleep(2)
    else:
        raise RuntimeError("api failed to start")
    state["producer"] = connect_kafka()
    thread = threading.Thread(target=scorer_loop, name="scorer", daemon=True)
    thread.start()
    yield
    state["stop"].set()
    if state["producer"] is not None:
        state["producer"].flush()
        state["producer"].close()
    if state["db"] is not None:
        state["db"].close()


app = FastAPI(title="Churn Flow API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.get("/health")
def health() -> dict[str, Any]:
    try:
        state["redis"].ping()
        redis_ok = True
    except Exception:
        redis_ok = False
    return {
        "ok": redis_ok and state["model"] is not None,
        "model_version": state["model_version"],
        "redis": redis_ok,
    }


@app.get("/customers")
def customers(risk: str | None = Query(default=None)) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for key in state["redis"].scan_iter(match="score:*", count=200):
        customer_id = key.split(":", 1)[1]
        data = state["redis"].hgetall(key)
        if not data:
            continue
        row = {
            "customer_id": customer_id,
            "score": float(data["score"]),
            "risk": data.get("risk", "LOW"),
            "model_version": data.get("model_version"),
            "scored_at": data.get("scored_at"),
            "latency_ms": float(data["latency_ms"]) if data.get("latency_ms") else None,
        }
        if risk and row["risk"].lower() != risk.lower():
            continue
        rows.append(row)
    rows.sort(key=lambda item: item["score"], reverse=True)
    return {"customers": rows, "count": len(rows)}


@app.get("/customers/{customer_id}")
def customer_detail(customer_id: str) -> dict[str, Any]:
    features = state["redis"].hgetall(features_key(customer_id))
    score = state["redis"].hgetall(score_key(customer_id))
    if not features and not score:
        raise HTTPException(status_code=404, detail="unknown customer")
    history = prediction_history(state["db"], customer_id)
    return {
        "customer_id": customer_id,
        "features": features,
        "latest_score": score,
        "history": history,
    }


@app.post("/predict/{customer_id}")
def predict(customer_id: str) -> dict[str, Any]:
    return score_customer(customer_id)


@app.get("/models")
def models() -> dict[str, Any]:
    return {"models": list_models(state["db"]), "serving": state["model_version"]}


@app.post("/models/retrain")
def retrain() -> dict[str, str]:
    state["redis"].set("retrain:requested", "1")
    return {"status": "queued"}


@app.get("/drift/latest")
def drift_latest() -> dict[str, Any]:
    rows = latest_drift_by_kind(state["db"])

    def payload(kind: str) -> dict[str, Any] | None:
        row = rows.get(kind)
        if row is None:
            return None
        created = row["created_at"]
        return {
            "psi": row["psi"],
            "metrics": row["metrics"],
            "reference_id": row["reference_id"],
            "created_at": created.isoformat() if created is not None else None,
        }

    data = payload("data")
    drifting = bool(data and (data.get("metrics") or {}).get("drifting"))
    status = "pending" if data is None else ("drifting" if drifting else "healthy")
    return {
        "status": status,
        "threshold": 0.20,
        "data_drift": data,
        "prediction_drift": payload("prediction"),
        "performance": payload("performance"),
        "note": "Data and prediction drift are immediate. Model performance waits on 14-day labels and is not inferred from PSI.",
    }


@app.get("/pipeline")
def pipeline() -> dict[str, Any]:
    stats = pipeline_stats(state["db"])
    last_event = stats["last_event_ts"]
    return {
        "active_model": state["model_version"],
        "events": stats["events"],
        "last_event_ts": last_event.isoformat() if last_event is not None else None,
        "p95_prediction_latency_ms": stats["p95_ms"],
        "predictions_last_5m": stats["predictions_5m"],
        "slo": {
            "event_to_prediction_p95_ms": 2000,
            "api_predict_p95_ms": 1000,
        },
    }
