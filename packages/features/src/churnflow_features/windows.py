from __future__ import annotations

from datetime import datetime, timedelta

from churnflow_features.constants import LOOKBACK_DAYS
from churnflow_features.schema import Event, as_utc


def window_start(observation_time: datetime, lookback_days: int = LOOKBACK_DAYS) -> datetime:
    return as_utc(observation_time) - timedelta(days=lookback_days)


def events_at_or_before(
    events: list[Event],
    observation_time: datetime,
) -> list[Event]:
    """Include events whose event time is <= T. Future events are dropped."""
    t = as_utc(observation_time)
    return [event for event in events if event.ts <= t]


def events_in_feature_window(
    events: list[Event],
    observation_time: datetime,
    lookback_days: int = LOOKBACK_DAYS,
) -> list[Event]:
    """Events in [T - lookback, T]. Strictly future events never enter features."""
    t = as_utc(observation_time)
    start = window_start(t, lookback_days)
    return [event for event in events if start <= event.ts <= t]
