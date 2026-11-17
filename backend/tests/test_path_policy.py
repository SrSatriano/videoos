from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Asset, Batch, PublishTask, RenderJob, RenderedVideo, Template
from app.services.seed import DEFAULT_RECIPE

from conftest import DATA_ROOT


client = TestClient(app)


def create_approved_render() -> str:
    video_path = DATA_ROOT / "renders" / f"{uuid4().hex}.mp4"
    thumbnail_path = DATA_ROOT / "thumbnails" / "renders" / f"{uuid4().hex}.jpg"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.write_bytes(b"rendered video")
    thumbnail_path.write_bytes(b"thumb")

    with SessionLocal() as db:
        asset = Asset(
            original_path=str(video_path),
            stored_path=str(video_path),
            filename=video_path.name,
            sha256=uuid4().hex + uuid4().hex,
            size_bytes=video_path.stat().st_size,
            duration_seconds=12,
            width=720,
            height=1280,
            fps=30,
            orientation="vertical",
            metadata_status="ready",
        )
        template = Template(
            name=f"Template {uuid4().hex[:6]}",
            description="",
            recipe_json=json.dumps(DEFAULT_RECIPE, ensure_ascii=False),
        )
        db.add(asset)
        db.add(template)
        db.flush()
        batch = Batch(name=f"Lote {uuid4().hex[:6]}", template_id=template.id, total_jobs=1)
        db.add(batch)
        db.flush()
        job = RenderJob(batch_id=batch.id, asset_id=asset.id, template_id=template.id, status="completed")
        db.add(job)
        db.flush()
        rendered = RenderedVideo(
            job_id=job.id,
            asset_id=asset.id,
            template_id=template.id,
            path=str(video_path),
            thumbnail_path=str(thumbnail_path),
            duration_seconds=12,
            width=720,
            height=1280,
            status="approved",
        )
        db.add(rendered)
        db.commit()
        db.refresh(rendered)
        return rendered.id


def test_settings_rejects_directory_outside_allowed_roots() -> None:
    outside_dir = DATA_ROOT.parent / "outside-settings"

    response = client.post("/api/system/settings", json={"renders_dir": str(outside_dir)})

    assert response.status_code == 400
    assert "renders_dir fora das pastas permitidas" in response.json()["detail"]


def test_settings_accepts_directory_inside_data_root() -> None:
    safe_dir = DATA_ROOT / "custom-renders"

    response = client.post("/api/system/settings", json={"renders_dir": str(safe_dir)})

    assert response.status_code == 200
    assert response.json()["renders_dir"] == str(safe_dir.resolve())


def test_publish_package_rejects_output_dir_outside_allowed_roots() -> None:
    rendered_id = create_approved_render()
    outside_dir = DATA_ROOT.parent / "outside-packages"

    response = client.post(
        "/api/publish-packages",
        json={
            "rendered_video_ids": [rendered_id],
            "platforms": ["instagram_reels"],
            "caption": "teste",
            "hashtags": ["videoos"],
            "output_dir": str(outside_dir),
        },
    )

    assert response.status_code == 400
    assert "output_dir fora das pastas permitidas" in response.json()["detail"]


def test_batch_creation_rejects_output_dir_outside_allowed_roots() -> None:
    video_path = DATA_ROOT / "incoming-batch-policy.mp4"
    video_path.write_bytes(b"batch policy bytes")
    outside_dir = DATA_ROOT.parent / "outside-batches"

    with SessionLocal() as db:
        asset = Asset(
            original_path=str(video_path),
            stored_path=str(video_path),
            filename=video_path.name,
            sha256=uuid4().hex + uuid4().hex,
            size_bytes=video_path.stat().st_size,
            duration_seconds=12,
            width=720,
            height=1280,
            fps=30,
            orientation="vertical",
            metadata_status="ready",
        )
        template = Template(
            name=f"Template {uuid4().hex[:6]}",
            description="",
            recipe_json=json.dumps(DEFAULT_RECIPE, ensure_ascii=False),
        )
        db.add(asset)
        db.add(template)
        db.commit()
        asset_id = asset.id
        template_id = template.id

    response = client.post(
        "/api/batches",
        json={
            "name": "Lote bloqueado",
            "template_id": template_id,
            "asset_ids": [asset_id],
            "variations": 1,
            "output_dir": str(outside_dir),
        },
    )

    assert response.status_code == 400
    assert "output_dir fora das pastas permitidas" in response.json()["detail"]


def test_publish_package_accepts_output_dir_inside_data_root() -> None:
    rendered_id = create_approved_render()
    output_dir = DATA_ROOT / "manual-packages"

    response = client.post(
        "/api/publish-packages",
        json={
            "rendered_video_ids": [rendered_id],
            "platforms": ["instagram_reels"],
            "caption": "teste",
            "hashtags": ["videoos"],
            "output_dir": str(output_dir),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    package_dir = payload["created"][0]["package_dir"]
    assert package_dir.startswith(str(output_dir.resolve()))
    package_path = Path(package_dir)
    metadata = json.loads((package_path / "metadata.json").read_text(encoding="utf-8"))
    quality_report = json.loads((package_path / "quality-report.json").read_text(encoding="utf-8"))
    assert metadata["quality_report"] == "quality-report.json"
    assert quality_report["schema_version"] == "videoos-quality-report/v2"
    assert quality_report["rendered_video_id"] == rendered_id
    assert quality_report["source"] == "ffprobe_loudnorm_and_render_metadata"
    assert quality_report["actual"]["file_size_bytes"] > 0
    assert "loudness" in quality_report["actual"]
    assert {check["id"] for check in quality_report["checks"]} >= {
        "render_approved",
        "resolution_matches_platform",
        "duration_available",
        "audio_signal_valid",
    }
    assert "audio_issues" in quality_report

    report_response = client.get(f"/api/publish-tasks/{payload['created'][0]['id']}/quality-report")
    assert report_response.status_code == 200
    assert report_response.json()["schema_version"] == "videoos-quality-report/v2"
    assert "attachment" in report_response.headers["content-disposition"]


def test_publish_quality_report_rejects_package_path_outside_allowed_roots(tmp_path: Path) -> None:
    rendered_id = create_approved_render()
    response = client.post(
        "/api/publish-packages",
        json={
            "rendered_video_ids": [rendered_id],
            "platforms": ["instagram_reels"],
            "caption": "teste",
            "hashtags": ["videoos"],
        },
    )
    assert response.status_code == 200
    task_id = response.json()["created"][0]["id"]
    outside_dir = tmp_path / "outside-package"
    outside_dir.mkdir()
    (outside_dir / "quality-report.json").write_text("{}", encoding="utf-8")
    with SessionLocal() as db:
        task = db.get(PublishTask, task_id)
        assert task is not None
        task.package_dir = str(outside_dir)
        db.commit()

    report_response = client.get(f"/api/publish-tasks/{task_id}/quality-report")

    assert report_response.status_code == 400
    assert "package_dir fora das pastas permitidas" in report_response.json()["detail"]


def test_publish_package_reuses_render_analysis_across_platforms(monkeypatch) -> None:
    from app.routes import publish

    rendered_id = create_approved_render()
    calls = 0

    def fake_analyze_render(_db, rendered):
        nonlocal calls
        calls += 1
        return (
            {
                "width": rendered.width,
                "height": rendered.height,
                "duration_seconds": rendered.duration_seconds,
                "size_bytes": Path(rendered.path).stat().st_size,
                "render_seconds": rendered.render_seconds,
                "peak_rss_bytes": rendered.peak_rss_bytes,
                "fps": 30.0,
                "bitrate_kbps": 1_500.0,
                "video_codec": "h264",
                "audio_codec": "aac",
                "audio_sample_rate_hz": 48_000,
                "audio_channels": 2,
                "has_audio": True,
                "container_format": "mov,mp4,m4a,3gp,3g2,mj2",
                "loudness": {"status": "measured", "integrated_lufs": -14.0},
            },
            {"status": "miss"},
        )

    monkeypatch.setattr(publish, "analyze_render", fake_analyze_render)

    response = client.post(
        "/api/publish-packages",
        json={
            "rendered_video_ids": [rendered_id],
            "platforms": ["instagram_reels", "tiktok", "youtube_shorts"],
            "caption": "teste",
            "hashtags": ["videoos"],
        },
    )

    assert response.status_code == 200
    assert response.json()["count"] == 3
    assert calls == 1


def test_template_creation_rejects_broll_path_outside_allowed_roots() -> None:
    recipe = {
        **DEFAULT_RECIPE,
        "broll": [{"path": str(DATA_ROOT.parent / "unsafe-broll.mp4"), "start": 0, "end": 1}],
    }

    response = client.post(
        "/api/templates",
        json={"name": f"Template {uuid4().hex[:6]}", "description": "", "recipe": recipe},
    )

    assert response.status_code == 422
    assert "broll[0].path fora das pastas permitidas" in response.json()["detail"]


def test_template_creation_rejects_split_secondary_path_outside_allowed_roots() -> None:
    recipe = {
        **DEFAULT_RECIPE,
        "split": {"secondary_video_path": str(DATA_ROOT.parent / "unsafe-split.mp4")},
    }

    response = client.post(
        "/api/templates",
        json={"name": f"Template {uuid4().hex[:6]}", "description": "", "recipe": recipe},
    )

    assert response.status_code == 422
    assert "split.secondary_video_path fora das pastas permitidas" in response.json()["detail"]


def test_template_creation_rejects_hook_path_outside_allowed_roots() -> None:
    recipe = {
        **DEFAULT_RECIPE,
        "hooks": [{"hook_video_path": str(DATA_ROOT.parent / "unsafe-hook.mp4")}],
    }

    response = client.post(
        "/api/templates",
        json={"name": f"Template {uuid4().hex[:6]}", "description": "", "recipe": recipe},
    )

    assert response.status_code == 422
    assert "hooks[0].hook_video_path fora das pastas permitidas" in response.json()["detail"]


def test_template_creation_rejects_watermark_image_path_outside_allowed_roots() -> None:
    recipe = {
        **DEFAULT_RECIPE,
        "watermark": {"image_path": str(DATA_ROOT.parent / "unsafe-logo.png")},
    }

    response = client.post(
        "/api/templates",
        json={"name": f"Template {uuid4().hex[:6]}", "description": "", "recipe": recipe},
    )

    assert response.status_code == 422
    assert "watermark.image_path fora das pastas permitidas" in response.json()["detail"]


def test_path_policy_validate_recipe_media_paths_helper() -> None:
    import pytest
    from app.services.path_policy import validate_recipe_media_paths, allowed_recipe_media_roots

    roots = allowed_recipe_media_roots()
    assert len(roots) >= 2

    unsafe_recipe = {
        **DEFAULT_RECIPE,
        "split": {"secondary_video_path": str(DATA_ROOT.parent / "unsafe.mp4")},
    }
    with pytest.raises(ValueError, match="split.secondary_video_path fora das pastas permitidas"):
        validate_recipe_media_paths(unsafe_recipe)

