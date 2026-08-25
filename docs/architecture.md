# Architecture

Churn Flow is an internal ML Ops platform. Simulated shoppers produce events; the platform scores churn risk, watches drift, and promotes models under a deterministic gate.

## Ingest path

```
Simulator
   ↓
Kafka  (commerce.events)
   ↓
Worker  (idempotent on event_id)
   ↓
Redis + PostgreSQL
   ↓
FastAPI  (active model)
   ↓
React ML Ops dashboard
```

Worker handles Kafka **at-least-once** delivery: unique `event_id` in Postgres, skip duplicates, do not double-count Redis.

## ML loop

```
PostgreSQL
   ↓
Drift Monitor
   ↓  (data PSI > 0.20)
Trainer
   ↓
model_versions  (promotion gate)
   ↓
FastAPI serves the active model
```

**Trainer** (train, evaluate, write artifact) and **Drift Monitor** (data drift, prediction drift, delayed performance, enqueue retrain) are separate modules. In V1 they share the `apps/trainer` container.

## Observation time

Features are built with `packages/features.build_features(events, observation_time=T)`.

- Include `event.ts <= T` only.
- Training: `T` is the observation timestamp of that row.
- Live serving: `T` is the **scoring timestamp**, not an unbound wall-clock `now()` inside aggregations.

## Services (V1)

| Component        | Role                                      | Phase 1          |
| ---------------- | ----------------------------------------- | ---------------- |
| PostgreSQL       | events, snapshots, predictions, models    | running          |
| Redis            | live feature hashes                       | running          |
| Kafka            | events, predictions, alerts               | running          |
| Prometheus       | scrape metrics                            | running          |
| Grafana          | infra dashboards (Prometheus provisioned) | running          |
| simulator        | synthetic events                          | running          |
| worker           | consume → Postgres + Redis features       | running          |
| api              | FastAPI serve + product metrics           | running          |
| trainer          | train LightGBM, promotion gate            | running          |
| web              | React ML Ops UI                           | running          |

No Kubernetes, MLflow, Spark, Airflow, or storefront in V1.
