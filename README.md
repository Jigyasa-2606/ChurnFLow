# Churn Flow

Internal **ML Ops** platform for e-commerce churn prediction.

Simulated shoppers produce events. There is no storefront. The users are the ML, data, and retention team: they watch live risk, model promotion, and drift.

Near-real-time, not hard real-time. Event → Kafka → features → score, with **measured** predict p95 (target under 2s end-to-end).

**GitHub About (paste this):**  
Internal ML Ops for e-commerce churn — Kafka ingest, leak-free features, LightGBM with a promotion gate, drift monitoring, Docker Compose, live ops dashboard.

---

## Live demo (present this)

There is no public cloud URL. The live demo is local Docker. Start it, then walk the screens.

```bash
git clone https://github.com/Jigyasa-2606/ChurnFlow.git
cd ChurnFlow
docker compose up -d
```

Wait until `docker compose ps` shows `web`, `api`, `worker`, `simulator`, and `trainer` as running. Then open:

| What to show | URL | Login |
| --- | --- | --- |
| **Product dashboard** | http://localhost:5173 | none |
| API docs | http://localhost:8000/docs | none |
| Grafana (latency charts) | http://localhost:3000 | `admin` / `churnflow` |

Grafana is infra metrics only. It does not open the product dashboard.

### 5-minute talk track

1. **Overview** (`/`) — 80 simulated customers, live scores, events/sec, measured predict p95. High-risk pile is expected: live features are minutes old vs a 90-day training window (data drift).
2. **Click one HIGH customer** — feature vector at observation time `T` (`event.ts ≤ T` only) and score history.
3. **Drift** — three different signals: data PSI vs training features (retrain if PSI > 0.20), prediction PSI vs reference scores, model performance **delayed** until 14-day labels exist.
4. **Models** — active LightGBM (~0.88 AUC). **Queue retrain** may still **reject** if the candidate does not beat active AUC by 0.01 with F1/logloss not worse. Serving stays on last-known-good.
5. **Pipeline** — API/Redis up, ingest counts, p95 vs SLO.
6. **Grafana** (optional, 30s) — Dashboards → Churn Flow → **Churn Flow serving**: request rate and latency graphs.

Stop:

```bash
docker compose down
```

---

## What it does

```
Simulator
   → Kafka (commerce.events)
   → Worker (idempotent on event_id)
   → Postgres + Redis features
   → FastAPI (active LightGBM)
   → React ML Ops UI
```

- **Features:** `[T-90d, T]`, include only `event.ts ≤ T`. Train and serve share `packages/features`.
- **Label:** purchase strictly after `T` through `T+14d` (yes → 0 retained, no → 1 churned). Live Kafka data is too new for those labels, so the trainer uses synthetic 90-day histories.
- **Promotion:** candidate AUC ≥ active + 0.01 **and** F1 ≥ active **and** logloss ≤ active.
- **Drift:** data vs training feature distribution of the active model; prediction vs that model’s scores on the same reference population; performance waits on labels.

## Stack

Python, LightGBM (XGBoost comparison only), FastAPI, Kafka, Redis, PostgreSQL, React, Docker Compose, Prometheus, Grafana.

## Spec

- [Architecture](docs/architecture.md)
- [ML: windows, leakage, drift, promotion](docs/ml.md)
- [Data model](docs/data-model.md)
- [Non-functional requirements](docs/nfr.md)
- [Runbook](docs/runbook.md)
