from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from churnflow_features.calculations import summarize
from churnflow_features.constants import LOOKBACK_DAYS
from churnflow_features.schema import Event, parse_events
from churnflow_features.windows import events_in_feature_window


def build_features(
    events: Sequence[Event | Mapping[str, Any]],
    observation_time: datetime,
    lookback_days: int = LOOKBACK_DAYS,
) -> dict[str, float]:
    """Feature vector at observation time T.

    Only events with event.ts <= T (and within the lookback window) are used.
    Training and serving must call this same function.
    """
    parsed = parse_events(events)
    windowed = events_in_feature_window(parsed, observation_time, lookback_days)
    return summarize(windowed, observation_time)
