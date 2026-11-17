from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, joinedload

from ..models import RenderJob, RenderedVideo


MINIMUM_CALIBRATION_SAMPLES = 3
MAX_SAMPLES_PER_PROFILE = 20
MAX_RECENT_METRIC_ROWS = 1000


def resolution_profile_id(width: int, height: int) -> str:
    if width >= 2160 or height >= 3840:
        return "4k"
    if width >= 1440 or height >= 2560:
        return "2k"
    return "1080p"


def backfill_render_metrics(db: Session) -> int:
    renders = (
        db.query(RenderedVideo)
        .options(joinedload(RenderedVideo.job))
        .filter((RenderedVideo.size_bytes.is_(None)) | (RenderedVideo.render_seconds.is_(None)))
        .all()
    )
    updated = 0
    for rendered in renders:
        changed = False
        if rendered.size_bytes is None:
            try:
                size_bytes = Path(rendered.path).stat().st_size
            except OSError:
                size_bytes = 0
            if size_bytes > 0:
                rendered.size_bytes = size_bytes
                changed = True
        job = rendered.job
        if rendered.render_seconds is None and job and job.started_at and job.finished_at:
            elapsed = (job.finished_at - job.started_at).total_seconds()
            if elapsed > 0:
                rendered.render_seconds = elapsed
                changed = True
        if changed:
            updated += 1
    if updated:
        db.commit()
    return updated


def render_performance_snapshot(db: Session) -> dict[str, Any]:
    rows = (
        db.query(
            RenderedVideo.template_id,
            RenderedVideo.width,
            RenderedVideo.height,
            RenderedVideo.duration_seconds,
            RenderedVideo.size_bytes,
            RenderedVideo.render_seconds,
            RenderedVideo.peak_rss_bytes,
            RenderJob.finished_at,
        )
        .join(RenderJob, RenderJob.id == RenderedVideo.job_id)
        .filter(
            RenderJob.status == "completed",
            RenderedVideo.width.is_not(None),
            RenderedVideo.height.is_not(None),
            RenderedVideo.duration_seconds > 0,
            RenderedVideo.size_bytes > 0,
            RenderedVideo.render_seconds > 0,
        )
        .order_by(RenderJob.finished_at.desc())
        .limit(MAX_RECENT_METRIC_ROWS)
        .all()
    )

    grouped: dict[tuple[str, str], list[Any]] = defaultdict(list)
    for row in rows:
        profile_id = resolution_profile_id(int(row.width), int(row.height))
        key = (str(row.template_id), profile_id)
        if len(grouped[key]) < MAX_SAMPLES_PER_PROFILE:
            grouped[key].append(row)

    profile_order = {"1080p": 0, "2k": 1, "4k": 2}
    profiles: list[dict[str, Any]] = []
    for (template_id, profile_id), samples in sorted(
        grouped.items(), key=lambda item: (item[0][0], profile_order[item[0][1]])
    ):
        total_duration = sum(float(sample.duration_seconds) for sample in samples)
        total_render_seconds = sum(float(sample.render_seconds) for sample in samples)
        total_bytes = sum(int(sample.size_bytes) for sample in samples)
        memory_samples = [
            int(sample.peak_rss_bytes)
            for sample in samples
            if sample.peak_rss_bytes is not None and int(sample.peak_rss_bytes) > 0
        ]
        profiles.append(
            {
                "template_id": template_id,
                "resolution": profile_id,
                "sample_count": len(samples),
                "wall_seconds_per_output_second": round(total_render_seconds / total_duration, 6),
                "bytes_per_output_second": round(total_bytes / total_duration, 3),
                "memory_sample_count": len(memory_samples),
                "peak_memory_bytes": max(memory_samples) if memory_samples else None,
                "last_completed_at": samples[0].finished_at.isoformat() if samples[0].finished_at else None,
            }
        )

    return {
        "minimum_samples": MINIMUM_CALIBRATION_SAMPLES,
        "max_samples_per_profile": MAX_SAMPLES_PER_PROFILE,
        "profiles": profiles,
    }
