from __future__ import annotations

import sys
from time import perf_counter

import pytest

from app.services import render as render_service
from app.services.render import RenderCanceledError, run_ffmpeg_command


def test_cooperative_cancel_terminates_active_process() -> None:
    polls = 0

    def should_cancel() -> bool:
        nonlocal polls
        polls += 1
        return polls >= 2

    started = perf_counter()
    with pytest.raises(RenderCanceledError, match="cancelado pelo usuario"):
        run_ffmpeg_command(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            should_cancel=should_cancel,
        )

    assert perf_counter() - started < 5


def test_run_ffmpeg_command_reports_highest_observed_rss(monkeypatch) -> None:
    samples = iter((100, 300, 200))

    def fake_rss(_pid: int) -> int:
        return next(samples, 200)

    monkeypatch.setattr(render_service, "_process_rss_bytes", fake_rss)

    completed = run_ffmpeg_command([sys.executable, "-c", "import time; time.sleep(0.7)"])

    assert completed.returncode == 0
    assert completed.peak_rss_bytes == 300
