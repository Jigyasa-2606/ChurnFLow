from __future__ import annotations

import json
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
from sklearn.metrics import f1_score, log_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from trainer.promote import Metrics

RANDOM_STATE = 7


def _metrics(y_true: np.ndarray, proba: np.ndarray) -> Metrics:
    pred = (proba >= 0.5).astype(int)
    return Metrics(
        auc=float(roc_auc_score(y_true, proba)),
        f1=float(f1_score(y_true, pred, zero_division=0)),
        logloss=float(log_loss(y_true, proba, labels=[0, 1])),
    )


def fit_lightgbm(x_train: np.ndarray, y_train: np.ndarray) -> lgb.LGBMClassifier:
    model = lgb.LGBMClassifier(
        n_estimators=80,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=RANDOM_STATE,
        verbose=-1,
    )
    model.fit(x_train, y_train)
    return model


def fit_xgboost(x_train: np.ndarray, y_train: np.ndarray) -> XGBClassifier:
    model = XGBClassifier(
        n_estimators=80,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.9,
        colsample_bytree=0.9,
        eval_metric="logloss",
        random_state=RANDOM_STATE,
        n_jobs=2,
    )
    model.fit(x_train, y_train)
    return model


def train_and_evaluate(
    x: np.ndarray,
    y: np.ndarray,
) -> tuple[lgb.LGBMClassifier, Metrics, Metrics, np.ndarray, np.ndarray]:
    x_train, x_val, y_train, y_val = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y,
    )
    lgbm = fit_lightgbm(x_train, y_train)
    xgb = fit_xgboost(x_train, y_train)
    lgbm_metrics = _metrics(y_val, lgbm.predict_proba(x_val)[:, 1])
    xgb_metrics = _metrics(y_val, xgb.predict_proba(x_val)[:, 1])
    return lgbm, lgbm_metrics, xgb_metrics, x_val, y_val


def save_artifact(
    model: lgb.LGBMClassifier,
    *,
    directory: Path,
    feature_names: list[str],
    lgbm_metrics: Metrics,
    xgb_metrics: Metrics,
    x_reference: np.ndarray,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, directory / "model.joblib")
    (directory / "feature_names.json").write_text(json.dumps(feature_names), encoding="utf-8")
    scores = model.predict_proba(x_reference)[:, 1]
    np.save(directory / "reference_features.npy", x_reference)
    np.save(directory / "reference_scores.npy", scores)
    meta = {
        "lightgbm": lgbm_metrics.__dict__,
        "xgboost": xgb_metrics.__dict__,
        "n_reference": int(len(x_reference)),
    }
    (directory / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
