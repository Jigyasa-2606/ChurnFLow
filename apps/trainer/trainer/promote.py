from __future__ import annotations

from dataclasses import dataclass


AUC_MARGIN = 0.01


@dataclass(frozen=True)
class Metrics:
    auc: float
    f1: float
    logloss: float


def should_promote(candidate: Metrics, active: Metrics | None) -> bool:
    """Deterministic promotion gate. A 0.001 AUC bump is not enough."""
    if active is None:
        return True
    return (
        candidate.auc >= active.auc + AUC_MARGIN
        and candidate.f1 >= active.f1
        and candidate.logloss <= active.logloss
    )
