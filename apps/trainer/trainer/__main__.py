from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from churnflow_features import FEATURES_VERSION

from trainer.dataset import build_matrix
from trainer.monitor import run_drift_check
from trainer.promote import should_promote
from trainer.registry import (
    active_metrics,
    connect,
    fetch_active,
    insert_version,
    promote_version,
)
from trainer.train import save_artifact, train_and_evaluate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("trainer")


def models_dir() -> Path:
    return Path(os.environ.get("MODELS_DIR", "/models"))


def n_samples() -> int:
    return int(os.environ.get("TRAIN_N_SAMPLES", "2500"))


def run_training_job(*, drift_triggered: bool = False) -> str:
    conn = connect()
    try:
        active = fetch_active(conn)
        x, y, names = build_matrix(n_samples())
        log.info("training matrix shape=%s churn_rate=%.3f features=%s", x.shape, float(y.mean()), names)
        model, lgbm_metrics, xgb_metrics, x_val, _y_val = train_and_evaluate(x, y)
        version = f"lgbm-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        artifact = models_dir() / version
        save_artifact(
            model,
            directory=artifact,
            feature_names=names,
            lgbm_metrics=lgbm_metrics,
            xgb_metrics=xgb_metrics,
            x_reference=x_val,
        )
        log.info(
            "candidate %s lgbm auc=%.3f f1=%.3f logloss=%.3f | xgboost auc=%.3f f1=%.3f logloss=%.3f",
            version,
            lgbm_metrics.auc,
            lgbm_metrics.f1,
            lgbm_metrics.logloss,
            xgb_metrics.auc,
            xgb_metrics.f1,
            xgb_metrics.logloss,
        )
        promote = should_promote(lgbm_metrics, active_metrics(active))
        insert_version(
            conn,
            model_version=version,
            features_version=FEATURES_VERSION,
            metrics=lgbm_metrics,
            drift_triggered=drift_triggered,
            promotion_status="candidate" if promote else "rejected",
        )
        if promote:
            promote_version(conn, version)
            log.info("PROMOTED %s (previous active=%s)", version, None if active is None else active["model_version"])
        else:
            log.info(
                "REJECTED %s vs active %s auc=%.3f f1=%.3f logloss=%.3f",
                version,
                active["model_version"] if active else "none",
                active["auc"] if active else 0.0,
                active["f1"] if active else 0.0,
                active["logloss"] if active else 0.0,
            )
        return version
    finally:
        conn.close()


def main() -> None:
    mode = os.environ.get("TRAIN_ON_START", "if_missing")
    conn = connect()
    try:
        active = fetch_active(conn)
    finally:
        conn.close()

    should_run = mode == "always" or (mode == "if_missing" and active is None)
    if should_run:
        run_training_job(drift_triggered=False)
    else:
        log.info("skipping train on start (TRAIN_ON_START=%s active=%s)", mode, None if active is None else active["model_version"])

    while True:
        try:
            import redis as redis_lib

            client = redis_lib.Redis.from_url(
                os.environ.get("REDIS_URL", "redis://redis:6379/0"),
                decode_responses=True,
            )
            conn = connect()
            try:
                active = fetch_active(conn)
                if active is not None:
                    result = run_drift_check(
                        conn,
                        client,
                        models_dir=models_dir(),
                        model_version=active["model_version"],
                    )
                    if result.get("drifting") and not client.get("drift:retrain_cooldown"):
                        log.info("DRIFT DETECTED psi=%.3f — enqueue retrain", result["data_psi"])
                        client.set("retrain:requested", "drift")
                        client.set("drift:retrain_cooldown", "1", ex=int(os.environ.get("DRIFT_RETRAIN_COOLDOWN_SEC", "300")))
            finally:
                conn.close()

            requested = client.get("retrain:requested")
            if requested:
                client.delete("retrain:requested")
                log.info("retrain requested via redis (%s)", requested)
                run_training_job(drift_triggered=requested == "drift")
        except Exception:
            log.exception("monitor loop failed")
        time.sleep(int(os.environ.get("DRIFT_INTERVAL_SEC", "30")))


if __name__ == "__main__":
    main()
