from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


def as_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


@dataclass(frozen=True)
class Event:
    event_id: str
    customer_id: str
    event_type: str
    ts: datetime
    payload: Mapping[str, Any]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> Event:
        ts = raw["ts"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return cls(
            event_id=str(raw["event_id"]),
            customer_id=str(raw["customer_id"]),
            event_type=str(raw["event_type"]),
            ts=as_utc(ts),
            payload=raw.get("payload") or {},
        )


def parse_events(events: Sequence[Event | Mapping[str, Any]]) -> list[Event]:
    parsed: list[Event] = []
    for item in events:
        parsed.append(item if isinstance(item, Event) else Event.from_mapping(item))
    return parsed
