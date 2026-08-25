from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

META_KEYS = {"_observation_time", "_features_version"}
HIGH_RISK_THRESHOLD = 0.7


def models_dir() -> Path:
    return Path(os.environ.get("MODELS_DIR", "/models"))


def features_from_redis_hash(raw: dict[str, str], feature_names: list[str]) -> tuple[np.ndarray, dict[str, float], str | None]:
    """Build the serving vector in training column order. Ignores Redis metadata keys."""
    values: dict[str, float] = {}
    for name, value in raw.items():
        if name in META_KEYS:
            continue
        values[name] = float(value)
    missing = [name for name in feature_names if name not in values]
    if missing:
        raise ValueError(f"missing features: {missing}")
    vector = np.asarray([values[name] for name in feature_names], dtype=np.float64)
    return vector, values, raw.get("_features_version")


def score_key(customer_id: str) -> str:
    return f"score:{customer_id}"


def features_key(customer_id: str) -> str:
    return f"features:{customer_id}"


def artifact_paths(model_version: str) -> tuple[Path, Path]:
    directory = models_dir() / model_version
    return directory / "model.joblib", directory / "feature_names.json"


def load_feature_names(model_version: str) -> list[str]:
    _, names_path = artifact_paths(model_version)
    return json.loads(names_path.read_text(encoding="utf-8"))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
