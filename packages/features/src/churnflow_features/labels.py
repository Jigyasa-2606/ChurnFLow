from __future__ import annotations

from datetime import datetime, timedelta

from churnflow_features.constants import EVENT_PURCHASE, LABEL_HORIZON_DAYS
from churnflow_features.schema import Event, as_utc


def churn_label(
    events: list[Event],
    observation_time: datetime,
    horizon_days: int = LABEL_HORIZON_DAYS,
) -> int:
    """1 = churned (no purchase strictly after T through T+horizon). 0 = retained.

    Purchases at or before T do not count. Only T < event.ts <= T+horizon.
    """
    t = as_utc(observation_time)
    end = t + timedelta(days=horizon_days)
    for event in events:
        if event.event_type != EVENT_PURCHASE:
            continue
        if t < event.ts <= end:
            return 0
    return 1
