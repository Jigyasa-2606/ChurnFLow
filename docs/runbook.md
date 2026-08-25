# Runbook

Local laptop. Docker required.

## How to start

```bash
cd /Users/jigyasaverma/Desktop/churn-flow
docker compose up -d
docker compose ps
```

Expect `healthy` for: `postgres`, `redis`, `kafka`, `prometheus`, `grafana`. `worker`, `simulator`, `trainer`, `api`, and `web` should be `running`. `kafka-init` should exit 0 after creating topics.

Dashboard: http://localhost:5173 (Overview is the live demo screen).

## How to stop

```bash
docker compose down
```

## How to reset

Destroys Kafka/Postgres/Redis/Prometheus/Grafana local volumes:

```bash
docker compose down -v
docker compose up -d
```

## How to inspect logs

```bash
docker compose logs -f trainer
docker compose logs -f simulator
docker compose logs -f worker
docker compose logs -f kafka
docker compose logs -f postgres
```

## Connectivity checks

```bash
docker compose exec postgres pg_isready -U churnflow -d churnflow
docker compose exec redis redis-cli ping
curl -sf http://localhost:9090/-/ready
curl -sf http://localhost:3000/api/health
```

Kafka topics (from the Kafka container):

```bash
docker compose exec kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --list
```

Expect: `commerce.events`, `churn.predictions`, `churn.alerts`.

Rows in Postgres (should increase while the simulator runs):

```bash
docker compose exec postgres psql -U churnflow -d churnflow \
  -c "SELECT count(*) AS events, count(DISTINCT customer_id) AS customers FROM events;"
```

Redis feature hashes and snapshots:

```bash
docker compose exec redis redis-cli KEYS 'features:*'
docker compose exec postgres psql -U churnflow -d churnflow \
  -c "SELECT count(*) FROM feature_snapshots;"
```

```bash
docker compose exec postgres psql -U churnflow -d churnflow \
  -c "SELECT model_version, auc, f1, logloss, promotion_status FROM model_versions;"
```

## How to retrain

The trainer trains on start if no active model (`TRAIN_ON_START=if_missing`). Force another run:

```bash
docker compose exec trainer python -c "from trainer.__main__ import run_training_job; run_training_job()"
```

A candidate is promoted only if AUC >= active + 0.01 and F1/logloss are not worse.

## API

http://localhost:8000/docs

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/pipeline
curl -s 'http://localhost:8000/customers?risk=high'
```

http://localhost:3000 — user `admin`, password `churnflow`. Prometheus is the default datasource. Provisioned dashboard: **Churn Flow serving** (API scrape, request rate, measured predict latency).
