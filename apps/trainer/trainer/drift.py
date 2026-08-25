"""Data drift vs training features. Prediction drift vs training-score reference.

PSI > 0.20 on data drift enqueues retraining. Prediction drift is logged only.
Model performance is not computed here — labels need T+14d.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

PSI_THRESHOLD = 0.20
META_KEYS = {"_observation_time", "_features_version"}


def population_stability_index(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    ref = np.asarray(reference, dtype=np.float64)
    cur = np.asarray(current, dtype=np.float64)
    ref = ref[np.isfinite(ref)]
    cur = cur[np.isfinite(cur)]
    if ref.size < 10 or cur.size < 10:
        return float("nan")
    quantiles = np.linspace(0, 1, bins + 1)
    edges = np.unique(np.quantile(ref, quantiles))
    if edges.size < 3:
        return 0.0
    edges = edges.astype(np.float64)
    edges[0] = -np.inf
    edges[-1] = np.inf
    ref_counts, _ = np.histogram(ref, bins=edges)
    cur_counts, _ = np.histogram(cur, bins=edges)
    ref_p = np.clip(ref_counts / max(ref_counts.sum(), 1), 1e-4, None)
    cur_p = np.clip(cur_counts / max(cur_counts.sum(), 1), 1e-4, None)
    ref_p = ref_p / ref_p.sum()
    cur_p = cur_p / cur_p.sum()
    return float(np.sum((cur_p - ref_p) * np.log(cur_p / ref_p)))


def ks_pvalue(reference: np.ndarray, current: np.ndarray) -> float:
    ref = np.asarray(reference, dtype=np.float64)
    cur = np.asarray(current, dtype=np.float64)
    ref = ref[np.isfinite(ref)]
    cur = cur[np.isfinite(cur)]
    if ref.size < 10 or cur.size < 10:
        return float("nan")
    from scipy.stats import ks_2samp

    return float(ks_2samp(ref, cur).pvalue)


def matrix_from_redis_hashes(
    hashes: list[dict[str, str]],
    feature_names: list[str],
) -> np.ndarray:
    rows: list[list[float]] = []
    for raw in hashes:
        try:
            rows.append([float(raw[name]) for name in feature_names])
        except (KeyError, TypeError, ValueError):
            continue
    if not rows:
        return np.empty((0, len(feature_names)))
    return np.asarray(rows, dtype=np.float64)


def scores_from_redis_hashes(hashes: list[dict[str, str]]) -> np.ndarray:
    values: list[float] = []
    for raw in hashes:
        if "score" not in raw:
            continue
        try:
            values.append(float(raw["score"]))
        except (TypeError, ValueError):
            continue
    return np.asarray(values, dtype=np.float64)


def feature_psi_report(
    reference: np.ndarray,
    current: np.ndarray,
    feature_names: list[str],
) -> dict[str, float]:
    per: dict[str, float] = {}
    for idx, name in enumerate(feature_names):
        per[name] = population_stability_index(reference[:, idx], current[:, idx])
    return per


def load_reference(models_dir: Path, model_version: str) -> tuple[np.ndarray, np.ndarray, list[str]]:
    directory = models_dir / model_version
    features = np.load(directory / "reference_features.npy")
    scores = np.load(directory / "reference_scores.npy")
    names = json.loads((directory / "feature_names.json").read_text(encoding="utf-8"))
    return features, scores, names
