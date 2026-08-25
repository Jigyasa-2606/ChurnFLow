# ML spec

## Observation window (no leakage)

Training example at observation time `T`:

```
Observation date T
        │
        ├── Features: T-90d → T
        │     include events where event.ts <= T
        │
        └── Label: T → T+14d
                         │
                  purchase strictly after T?
                 /        \
               YES        NO
               0          1
```

Rules:

- Features at `T` may only use events with `event.ts <= T`.
- The churn label uses purchases **strictly after T** through `T+14 days`.
- Training and serving call the same function:

```text
features = build_features(events=events, observation_time=T)
```

- Live serving sets `T` to the scoring timestamp.

Leakage tests must fail the build if a post-`T` event affects features, or if a purchase at-or-before `T` counts as the label.

## Feature set (initial)

Built from events in `[T-90d, T]`:

- recency (days since last purchase / last session)
- frequency and monetary value over 7d / 30d / 90d
- session count
- cart-abandon rate
- support tickets
- category diversity

`features_version` is recorded on every `model_versions` row.

## Model

- Served model: LightGBM binary classifier.
- Trainer also fits XGBoost and logs comparison metrics. Only LightGBM is promoted.

Metrics recorded: AUC, F1, logloss.

## Drift vs performance

These are three different signals.

| Signal              | Question                         | Reference (frozen)                                                                 | When      |
| ------------------- | -------------------------------- | ---------------------------------------------------------------------------------- | --------- |
| Data drift          | Did customer behavior change?    | **Training feature distribution** of the active model                               | Immediate |
| Prediction drift    | Did score distribution change?   | **Active model scores on that same training/reference evaluation population**      | Immediate |
| Model performance   | Is the model actually worse?     | Ground truth after the 14-day label window                                         | Delayed   |

Data-drift threshold: **PSI > 0.20** → create a retraining job.

Prediction drift is logged. It does **not** prove the model got worse.

Performance is measured when enough rows have reached `T+14d`.

## Promotion gate

Promote the candidate **only if all** of the following hold versus the active model:

- `candidate AUC >= active AUC + 0.01`
- `AND candidate F1 >= active F1`
- `AND candidate logloss <= active logloss`

Otherwise reject. A 0.001 AUC bump does not replace production.

Serving always uses `promotion_status = active`. Failed trains keep the last known good artifact.
