-- Churn Flow schema (applied on first Postgres boot).
-- events.event_id is unique so Kafka at-least-once redelivery is idempotent.

CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS events_customer_ts_idx ON events (customer_id, ts);

CREATE TABLE IF NOT EXISTS feature_snapshots (
    id BIGSERIAL PRIMARY KEY,
    customer_id TEXT NOT NULL,
    observation_time TIMESTAMPTZ NOT NULL,
    features_version TEXT NOT NULL,
    features JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (customer_id, observation_time, features_version)
);

CREATE TABLE IF NOT EXISTS predictions (
    id BIGSERIAL PRIMARY KEY,
    customer_id TEXT NOT NULL,
    score DOUBLE PRECISION NOT NULL,
    model_version TEXT NOT NULL,
    scoring_ts TIMESTAMPTZ NOT NULL,
    latency_ms DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS predictions_customer_idx ON predictions (customer_id, created_at DESC);

CREATE TABLE IF NOT EXISTS model_versions (
    model_version TEXT PRIMARY KEY,
    training_time TIMESTAMPTZ NOT NULL,
    features_version TEXT NOT NULL,
    auc DOUBLE PRECISION,
    f1 DOUBLE PRECISION,
    logloss DOUBLE PRECISION,
    drift_triggered BOOLEAN NOT NULL DEFAULT FALSE,
    promotion_status TEXT NOT NULL CHECK (
        promotion_status IN ('candidate', 'active', 'rejected', 'shadow')
    ),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS model_versions_one_active
    ON model_versions (promotion_status)
    WHERE promotion_status = 'active';

CREATE TABLE IF NOT EXISTS drift_reports (
    id BIGSERIAL PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('data', 'prediction', 'performance')),
    psi DOUBLE PRECISION,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    reference_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
