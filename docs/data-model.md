# Data model

## Kafka topics

| Topic               | Producer        | Payload                                      |
| ------------------- | --------------- | -------------------------------------------- |
| `commerce.events`   | simulator       | event schema below                           |
| `churn.predictions` | api / worker    | customer_id, score, model_version, ts        |
| `churn.alerts`      | api             | score >= 0.7                                 |

Host bootstrap: `localhost:9092`. In-compose: `kafka:29092`.

## Event schema

```json
{
  "event_id": "evt_123",
  "customer_id": "cust_42",
  "event_type": "purchase",
  "ts": "2026-08-25T15:20:10Z",
  "payload": {
    "amount": 1499,
    "category": "electronics"
  }
}
```

`event_id` is globally unique. Phase 1 simulator types: `page_view`, `add_to_cart`, `purchase`, `session_end`, `support_ticket`.

## PostgreSQL (`churnflow`)

### events

Idempotency root. Unique `event_id` so at-least-once Kafka redelivery does not insert twice.

| Column       | Type        | Notes                    |
| ------------ | ----------- | ------------------------ |
| event_id     | text PK     | unique                   |
| customer_id  | text        |                          |
| event_type   | text        |                          |
| ts           | timestamptz | event time               |
| payload      | jsonb       |                          |
| ingested_at  | timestamptz | wall clock of insert     |

### feature_snapshots

One row per (customer_id, observation_time T, features_version). Features computed with `event.ts <= T`.

### predictions

customer_id, score, model_version, scoring_ts (T), latency_ms.

### model_versions

model_version, training_time, features_version, auc, f1, logloss, drift_triggered, promotion_status (`candidate` \| `active` \| `rejected` \| `shadow`).

### drift_reports

kind (`data` \| `prediction` \| `performance`), psi / metrics, reference_id, created_at.

Schema is applied by `infra/postgres/init.sql` on first Postgres boot.

## Redis keys (after ingest milestone)

| Key                    | Type | Contents                          |
| ---------------------- | ---- | --------------------------------- |
| `features:{customer_id}` | hash | latest live feature vector        |
| `score:{customer_id}`    | hash | latest score + model_version      |
| `processed:{event_id}`   | string | optional duplicate guard (TTL)  |
