from __future__ import annotations

from datetime import datetime, timedelta


def build_schedule(start_at: datetime, count: int, interval_minutes: int, platforms: list[str]) -> list[dict]:
    slots = []
    for index in range(count):
        for platform in platforms:
            slots.append(
                {
                    "publish_at": start_at + timedelta(minutes=interval_minutes * index),
                    "platform": platform,
                    "status": "planned",
                    "order_index": index + 1,
                }
            )
    return slots
