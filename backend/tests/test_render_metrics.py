from __future__ import annotations

from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Asset, Batch, RenderJob, RenderedVideo, Template, now_utc
from app.services.render_metrics import backfill_render_metrics, render_performance_snapshot


def metric_session(tmp_path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path / 'metrics.sqlite3'}", future=True)
    Base.metadata.create_all(engine)
    return Session(engine)


def seed_metric_dependencies(db: Session):
    asset = Asset(
        original_path="source.mp4",
        stored_path="source.mp4",
        filename="source.mp4",
        sha256="a" * 64,
        size_bytes=100,
    )
    template = Template(name="Template metricas", description="", recipe_json="{}")
    db.add_all([asset, template])
    db.flush()
    batch = Batch(name="Lote metricas", template_id=template.id, total_jobs=3)
    db.add(batch)
    db.flush()
    return asset, template, batch


def test_render_performance_snapshot_uses_weighted_recent_samples(tmp_path):
    with metric_session(tmp_path) as db:
        asset, template, batch = seed_metric_dependencies(db)
        finished_at = now_utc()
        for index, duration in enumerate((10.0, 20.0, 30.0), start=1):
            job = RenderJob(
                batch_id=batch.id,
                asset_id=asset.id,
                template_id=template.id,
                variation_index=index,
                status="completed",
                finished_at=finished_at + timedelta(seconds=index),
            )
            db.add(job)
            db.flush()
            db.add(
                RenderedVideo(
                    job_id=job.id,
                    asset_id=asset.id,
                    template_id=template.id,
                    path=f"render-{index}.mp4",
                    duration_seconds=duration,
                    width=1080,
                    height=1920,
                    size_bytes=int(duration * 100),
                    render_seconds=duration * 2,
                    peak_rss_bytes=index * 1_000,
                )
            )
        db.commit()

        snapshot = render_performance_snapshot(db)
        template_id = template.id

    assert snapshot["minimum_samples"] == 3
    assert snapshot["profiles"] == [
        {
            "template_id": template_id,
            "resolution": "1080p",
            "sample_count": 3,
            "wall_seconds_per_output_second": 2.0,
            "bytes_per_output_second": 100.0,
            "memory_sample_count": 3,
            "peak_memory_bytes": 3_000,
            "last_completed_at": (finished_at + timedelta(seconds=3)).isoformat(),
        }
    ]


def test_backfill_render_metrics_uses_existing_file_and_job_timestamps(tmp_path):
    output_path = tmp_path / "existing.mp4"
    output_path.write_bytes(b"existing-render")
    with metric_session(tmp_path) as db:
        asset, template, batch = seed_metric_dependencies(db)
        started_at = now_utc()
        job = RenderJob(
            batch_id=batch.id,
            asset_id=asset.id,
            template_id=template.id,
            status="completed",
            started_at=started_at,
            finished_at=started_at + timedelta(seconds=12),
        )
        db.add(job)
        db.flush()
        rendered = RenderedVideo(
            job_id=job.id,
            asset_id=asset.id,
            template_id=template.id,
            path=str(output_path),
            duration_seconds=6,
            width=1080,
            height=1920,
        )
        db.add(rendered)
        db.commit()

        assert backfill_render_metrics(db) == 1
        db.refresh(rendered)

        assert rendered.size_bytes == len(b"existing-render")
        assert rendered.render_seconds == 12
