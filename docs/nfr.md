# Non-functional requirements

## Latency

| Path                                      | Target      |
| ----------------------------------------- | ----------- |
| Event → feature update                    | < 500 ms    |
| Feature → prediction                      | < 500 ms    |
| Full path event → prediction p95          | < 2 s       |
| API prediction p95                        | < 1 s       |

The Overview UI must display **measured** p95, not the word "real-time".

## Reliability

- Kafka consumer resumes from committed offsets after restart.
- API remains available if the simulator stops.
- Serving falls back to the last known good model if a candidate train fails.
- Worker processing is **idempotent** on `event_id` (Postgres unique constraint; Redis counters must not increment twice).

## Data

- For observation time `T`, include events where `event.ts <= T` only.
- Live serving uses the scoring timestamp as `T`.
- Training and serving share `packages/features`. Every model row stores `features_version`.

## Model

Promote candidate only if **all** hold:

- `candidate AUC >= active AUC + 0.01`
- `candidate F1 >= active F1`
- `candidate logloss <= active logloss`

Data-drift retrain threshold: **PSI > 0.20** against the **training feature distribution** of the active model.

Prediction-drift reference: **active model scores on that training/reference evaluation population**.
