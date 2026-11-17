from __future__ import annotations

import subprocess
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Asset, Batch, RenderJob, RenderedVideo, Template
from app.services.seed import DEFAULT_RECIPE

from conftest import DATA_ROOT

client = TestClient(app)


def test_asset_integrity_file_missing() -> None:
    asset_id = "missing-asset-id"
    with SessionLocal() as db:
        # Clean up any existing record
        existing = db.get(Asset, asset_id)
        if existing:
            db.delete(existing)
            db.commit()

        asset = Asset(
            id=asset_id,
            original_path=str(DATA_ROOT / "missing_file.mp4"),
            stored_path=str(DATA_ROOT / "missing_file.mp4"),
            filename="missing_file.mp4",
            sha256="some-sha256-hash",
            size_bytes=1000,
            duration_seconds=10.0,
            width=1080,
            height=1920,
            fps=30,
            orientation="vertical",
            metadata_status="ready",
        )
        db.add(asset)
        db.commit()

    response = client.post(f"/api/quality/assets/{asset_id}/integrity")
    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is False
    assert payload["error_type"] == "file_missing"
    assert "ausente" in payload["message"].lower()


def test_asset_integrity_metadata_corrupt(monkeypatch) -> None:
    asset_id = "corrupt-metadata-asset"
    dummy_file = DATA_ROOT / "corrupt_meta.mp4"
    dummy_file.parent.mkdir(parents=True, exist_ok=True)
    dummy_file.write_bytes(b"0" * 100)

    with SessionLocal() as db:
        existing = db.get(Asset, asset_id)
        if existing:
            db.delete(existing)
            db.commit()

        asset = Asset(
            id=asset_id,
            original_path=str(dummy_file),
            stored_path=str(dummy_file),
            filename="corrupt_meta.mp4",
            sha256="some-other-sha256-hash",
            size_bytes=100,
            duration_seconds=10.0,
            width=1080,
            height=1920,
            fps=30,
            orientation="vertical",
            metadata_status="ready",
        )
        db.add(asset)
        db.commit()

    # Mock ffprobe to raise exception
    from app.services import quality

    def mock_raise(_path):
        raise Exception("ffprobe error")

    monkeypatch.setattr(quality, "ffprobe_metadata", mock_raise)

    response = client.post(f"/api/quality/assets/{asset_id}/integrity")
    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is False
    assert payload["error_type"] == "metadata_corrupt"


def test_asset_integrity_valid_ffmpeg_success(monkeypatch) -> None:
    asset_id = "valid-asset-id"
    dummy_file = DATA_ROOT / "valid_file.mp4"
    dummy_file.parent.mkdir(parents=True, exist_ok=True)
    dummy_file.write_bytes(b"0" * 100)

    with SessionLocal() as db:
        existing = db.get(Asset, asset_id)
        if existing:
            db.delete(existing)
            db.commit()

        asset = Asset(
            id=asset_id,
            original_path=str(dummy_file),
            stored_path=str(dummy_file),
            filename="valid_file.mp4",
            sha256="valid-sha256-hash",
            size_bytes=100,
            duration_seconds=10.0,
            width=1080,
            height=1920,
            fps=30,
            orientation="vertical",
            metadata_status="ready",
        )
        db.add(asset)
        db.commit()

    from app.services import quality
    monkeypatch.setattr(quality, "ffprobe_metadata", lambda _path: {"width": 1080, "height": 1920, "duration_seconds": 10.0})

    # Mock subprocess.run to succeed
    class DummyCompletedProcess:
        returncode = 0
        stderr = b""

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: DummyCompletedProcess())

    response = client.post(f"/api/quality/assets/{asset_id}/integrity")
    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is True
    assert payload["error_type"] is None
    assert payload["details"]["width"] == 1080


def test_render_integrity_decode_failed(monkeypatch) -> None:
    render_id = "render-failed-decode"
    dummy_file = DATA_ROOT / "renders" / f"{uuid4().hex}.mp4"
    dummy_file.parent.mkdir(parents=True, exist_ok=True)
    dummy_file.write_bytes(b"0" * 100)

    with SessionLocal() as db:
        # Clean up existing render and job if any
        existing_render = db.get(RenderedVideo, render_id)
        if existing_render:
            db.delete(existing_render)
            db.commit()

        template = Template(name="Temp1", description="", recipe_json=DEFAULT_RECIPE.__repr__())
        db.add(template)
        db.flush()
        batch = Batch(name="B1", template_id=template.id, total_jobs=1)
        db.add(batch)
        db.flush()
        asset = Asset(
            original_path="dummy",
            stored_path="dummy",
            filename="dummy",
            sha256="hash-abc",
            size_bytes=10,
            duration_seconds=1.0,
            width=100,
            height=100,
            fps=10,
            orientation="square",
            metadata_status="ready",
        )
        db.add(asset)
        db.flush()
        job = RenderJob(batch_id=batch.id, asset_id=asset.id, template_id=template.id, status="completed")
        db.add(job)
        db.flush()
        rendered = RenderedVideo(
            id=render_id,
            job_id=job.id,
            asset_id=asset.id,
            template_id=template.id,
            path=str(dummy_file),
            duration_seconds=10.0,
            width=1080,
            height=1920,
            status="pending_review",
        )
        db.add(rendered)
        db.commit()

    from app.services import quality
    monkeypatch.setattr(quality, "ffprobe_metadata", lambda _path: {"width": 1080, "height": 1920, "duration_seconds": 10.0})

    # Mock subprocess.run to fail
    class DummyFailedProcess:
        returncode = 1
        stderr = b"FFmpeg failed decode test"

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: DummyFailedProcess())

    response = client.post(f"/api/quality/renders/{render_id}/integrity")
    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is False
    assert payload["error_type"] == "decode_failed"
    assert "failed decode test" in payload["message"]
