# Churn Flow

Internal **ML Operations** platform for e-commerce churn prediction.

Simulated shoppers are the data source. There is no customer-facing store. The users of this product are the ML, data, and retention team.

This is **near-real-time**, not hard real-time. Event → Kafka → features → prediction target: **p95 under 2 seconds**. The dashboard will show measured latency, not a slogan.

## Current milestone

Simulator → Kafka (`commerce.events`) → worker → PostgreSQL.

The worker is **idempotent** on `event_id` (`ON CONFLICT DO NOTHING`) so Kafka at-least-once redelivery does not insert twice. After each event it rebuilds that customer's features with `build_features(..., observation_time=T)` (`event.ts <= T`), writes Redis `features:{id}`, and stores a Postgres snapshot.

The **API** serves the **active** model (currently the realistic AUC ~0.88 LightGBM). It scores Redis feature hashes every few seconds. OpenAPI: http://localhost:8000/docs

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/pipeline
curl -s http://localhost:8000/drift/latest
curl -s http://localhost:8000/customers?risk=high
curl -s -X POST http://localhost:8000/predict/cust_0001
```

## Start

```bash
docker compose up -d
docker compose ps
```

You should see Kafka, Redis, Postgres, Prometheus, Grafana, worker, simulator, trainer, API, and the dashboard (`web`) up. Confirm ingest:

```bash
docker compose exec postgres psql -U churnflow -d churnflow -c "SELECT count(*) FROM events;"
```

The count should rise every few seconds.

Live feature hashes:

```bash
docker compose exec redis redis-cli KEYS 'features:*'
docker compose exec redis redis-cli HGETALL features:cust_0001
```

| Service    | URL / port            | Notes                    |
| ---------- | --------------------- | ------------------------ |
| PostgreSQL | `localhost:5432`      | user/pass/db: `churnflow` |
| Redis      | `localhost:6379`      |                          |
| Kafka      | `localhost:9092`      | host clients             |
| Kafka      | `kafka:29092`         | other Compose services   |
| Prometheus | http://localhost:9090 |                          |
| API        | http://localhost:8000 | `/docs` OpenAPI          |
| Web        | http://localhost:5173 | ML Ops dashboard         |
| Grafana    | http://localhost:3000 | admin / `churnflow`      |

Stop:

```bash
docker compose down
```

Reset volumes (destroys local data):

```bash
docker compose down -v
```

See [docs/runbook.md](docs/runbook.md) for logs and later retrain/reset steps.

## Shared features

Training and serving use the same package: `packages/features`.

```bash
cd packages/features
python -m pip install -e ".[dev]"
pytest -q
```

`build_features(events, observation_time=T)` includes only `event.ts <= T`.

## Spec

- [Architecture](docs/architecture.md)
- [ML: windows, leakage, drift, promotion](docs/ml.md)
- [Data model](docs/data-model.md)
- [Non-functional requirements](docs/nfr.md)
- [Runbook](docs/runbook.md)
