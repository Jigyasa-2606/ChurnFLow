from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from trainer.drift import (
    PSI_THRESHOLD,
    feature_psi_report,
    ks_pvalue,
    load_reference,
    matrix_from_redis_hashes,
    population_stability_index,
    scores_from_redis_hashes,
)
from trainer.registry import insert_drift_report

log = logging.getLogger("trainer")


def collect_feature_hashes(redis_client: Any) -> list[dict[str, str]]:
    hashes: list[dict[str, str]] = []
    for key in redis_client.scan_iter(match="features:*", count=200):
        raw = redis_client.hgetall(key)
        if raw:
            hashes.append(raw)
    return hashes


def collect_score_hashes(redis_client: Any) -> list[dict[str, str]]:
    hashes: list[dict[str, str]] = []
    for key in redis_client.scan_iter(match="score:*", count=200):
        raw = redis_client.hgetall(key)
        if raw:
            hashes.append(raw)
    return hashes


def run_drift_check(
    conn: Any,
    redis_client: Any,
    *,
    models_dir: Path,
    model_version: str,
    min_samples: int = 20,
) -> dict[str, Any]:
    reference_x, reference_scores, names = load_reference(models_dir, model_version)
    live_x = matrix_from_redis_hashes(collect_feature_hashes(redis_client), names)
    live_scores = scores_from_redis_hashes(collect_score_hashes(redis_client))

    if live_x.shape[0] < min_samples:
        log.info("drift skip: only %s live feature rows (need %s)", live_x.shape[0], min_samples)
        return {"skipped": True, "n_current": int(live_x.shape[0])}

    per_feature = feature_psi_report(reference_x, live_x, names)
    finite = [value for value in per_feature.values() if value == value]
    data_psi = max(finite) if finite else float("nan")
    pred_psi = (
        population_stability_index(reference_scores, live_scores)
        if live_scores.size >= min_samples
        else float("nan")
    )
    pred_ks = ks_pvalue(reference_scores, live_scores) if live_scores.size >= min_samples else float("nan")
    drifting = data_psi == data_psi and data_psi > PSI_THRESHOLD

    data_metrics = {
        "threshold": PSI_THRESHOLD,
        "max_psi": data_psi,
        "by_feature": per_feature,
        "n_reference": int(reference_x.shape[0]),
        "n_current": int(live_x.shape[0]),
        "drifting": drifting,
    }
    pred_metrics = {
        "psi": pred_psi,
        "ks_pvalue": pred_ks,
        "n_reference": int(reference_scores.size),
        "n_current": int(live_scores.size),
        "note": "Prediction drift is not proof the model got worse.",
    }
    performance_metrics = {
        "available": False,
        "labeled_rows": 0,
        "reason": "Ground-truth churn labels need purchases strictly after T through T+14d. Live observations are still inside that window.",
    }

    insert_drift_report(conn, kind="data", psi=data_psi, metrics=data_metrics, reference_id=model_version)
    insert_drift_report(conn, kind="prediction", psi=pred_psi, metrics=pred_metrics, reference_id=model_version)
    insert_drift_report(conn, kind="performance", psi=None, metrics=performance_metrics, reference_id=model_version)

    log.info(
        "drift data_max_psi=%.3f prediction_psi=%.3f drifting=%s n_live=%s ref=%s",
        data_psi,
        pred_psi,
        drifting,
        live_x.shape[0],
        model_version,
    )
    return {
        "skipped": False,
        "drifting": drifting,
        "data_psi": data_psi,
        "prediction_psi": pred_psi,
        "reference_id": model_version,
    }
