from datetime import timedelta

from trainer.dataset import DEFAULT_T, generate_customer_events
from trainer.promote import Metrics, should_promote
from churnflow_features import build_features, churn_label
from churnflow_features.schema import parse_events

import numpy as np


def test_tiny_auc_gain_is_not_enough() -> None:
    active = Metrics(auc=0.912, f1=0.80, logloss=0.40)
    candidate = Metrics(auc=0.913, f1=0.80, logloss=0.40)
    assert should_promote(candidate, active) is False


def test_promotion_requires_all_three() -> None:
    active = Metrics(auc=0.912, f1=0.80, logloss=0.40)
    assert should_promote(Metrics(0.922, 0.80, 0.40), active) is True
    assert should_promote(Metrics(0.922, 0.79, 0.39), active) is False
    assert should_promote(Metrics(0.922, 0.81, 0.41), active) is False


def test_first_model_promotes_when_no_active() -> None:
    assert should_promote(Metrics(0.60, 0.50, 0.70), None) is True


def test_dataset_hides_future_purchases_from_features() -> None:
    rng = np.random.default_rng(0)
    t = DEFAULT_T
    matched = False
    for i in range(40):
        events = generate_customer_events(rng, f"train_leak_{i}", t, will_churn=False)
        future = [e for e in events if e["event_type"] == "purchase" and e["ts"] > t]
        if not future:
            continue
        features = build_features(events, observation_time=t)
        only_past = [e for e in events if e["ts"] <= t]
        assert features == build_features(only_past, observation_time=t)
        matched = True
        break
    assert matched


def test_label_ignores_purchase_at_t() -> None:
    t = DEFAULT_T
    events = [
        {
            "event_id": "at_t",
            "customer_id": "c1",
            "event_type": "purchase",
            "ts": t,
            "payload": {"amount": 50, "category": "home"},
        }
    ]
    assert churn_label(parse_events(events), t) == 1
    events.append(
        {
            "event_id": "after",
            "customer_id": "c1",
            "event_type": "purchase",
            "ts": t + timedelta(days=1),
            "payload": {"amount": 50, "category": "home"},
        }
    )
    assert churn_label(parse_events(events), t) == 0
