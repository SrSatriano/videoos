from __future__ import annotations

from datetime import datetime

from app.services.calendar import build_schedule


def test_build_schedule_every_two_hours():
    slots = build_schedule(
        start_at=datetime(2026, 5, 29, 9, 0, 0),
        count=3,
        interval_minutes=120,
        platforms=["youtube_shorts"],
    )
    assert [slot["publish_at"].hour for slot in slots] == [9, 11, 13]
