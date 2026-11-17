from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Asset, Batch, RenderJob, RenderedVideo, Template
from app.services.seed import DEFAULT_RECIPE

from conftest import DATA_ROOT


client = TestClient(app)


def create_render(
    width: int,
    height: int,
    duration: float,
    size_bytes: int = 2_000_000,
    status: str = "pending_review",
) -> str:
    video_path = DATA_ROOT / "renders" / f"{uuid4().hex}.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.write_bytes(b"0" * size_bytes)
    with SessionLocal() as db:
        asset = Asset(
            original_path=str(video_path),
            stored_path=str(video_path),
            filename=video_path.name,
            sha256=uuid4().hex + uuid4().hex,
            size_bytes=size_bytes,
            duration_seconds=duration,
            width=width,
            height=height,
            fps=30,
            orientation="vertical" if height > width else "horizontal",
            metadata_status="ready",
        )
        template = Template(name=f"Template {uuid4().hex[:6]}", description="", recipe_json=DEFAULT_RECIPE.__repr__())
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
            duration_seconds=duration,
            width=width,
            height=height,
            size_bytes=size_bytes,
            render_seconds=8.25,
            peak_rss_bytes=256 * 1024 * 1024,
            status=status,
        )
        db.add(rendered)
        db.commit()
        db.refresh(rendered)
        return rendered.id


def test_quality_check_passes_vertical_short(monkeypatch) -> None:
    from app.services import quality

    rendered_id = create_render(1080, 1920, 54)
    monkeypatch.setattr(
        quality,
        "ffprobe_metadata",
        lambda _path: {
            "width": 1080,
            "height": 1920,
            "duration_seconds": 54,
            "fps": 30,
            "video_codec": "h264",
            "audio_codec": "aac",
            "audio_sample_rate_hz": 48_000,
            "audio_channels": 2,
            "container_format": "mov,mp4,m4a,3gp,3g2,mj2",
            "format_bit_rate_kbps": 2_800.0,
            "has_audio": True,
        },
    )
    monkeypatch.setattr(
        quality,
        "measure_audio_loudness",
        lambda _path: {
            "status": "measured",
            "integrated_lufs": -14.2,
            "true_peak_dbtp": -1.8,
            "loudness_range_lu": 4.1,
            "threshold_lufs": -24.0,
            "target_integrated_lufs": -14.0,
            "target_true_peak_dbtp": -1.5,
            "target_lra_lu": 11.0,
        },
    )

    response = client.post(f"/api/quality/renders/{rendered_id}", json={"platforms": ["instagram_reels", "tiktok", "youtube_shorts"]})

    assert response.status_code == 200
    payload = response.json()
    reports = payload["reports"]
    assert all(report["passed"] for report in reports)
    assert payload["safe_zone_guide"]["platform"] == "universal"
    assert payload["safe_zone_guide"]["right_pct"] >= 18
    assert all("safe_zone" in report for report in reports)
    assert payload["review_status"] == "pending_review"
    assert payload["package_ready"] is False
    assert payload["metadata"]["video_codec"] == "h264"
    assert payload["metadata"]["loudness"]["integrated_lufs"] == -14.2
    assert payload["metadata"]["render_seconds"] == 8.25
    assert payload["metadata"]["peak_rss_bytes"] == 256 * 1024 * 1024


def test_quality_check_marks_approved_render_ready(monkeypatch) -> None:
    from app.services import quality

    rendered_id = create_render(1080, 1920, 24, status="approved")
    monkeypatch.setattr(
        quality,
        "ffprobe_metadata",
        lambda _path: {
            "width": 1080,
            "height": 1920,
            "duration_seconds": 24,
            "fps": 30,
            "has_audio": False,
        },
    )

    response = client.post(
        f"/api/quality/renders/{rendered_id}",
        json={"platforms": ["instagram_reels", "tiktok", "youtube_shorts"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["review_status"] == "approved"
    assert payload["package_ready"] is True
    assert payload["metadata"]["loudness"]["status"] == "no_audio"


def test_quality_check_flags_wrong_youtube_duration(monkeypatch) -> None:
    from app.services import quality

    rendered_id = create_render(1920, 1080, 240)
    monkeypatch.setattr(quality, "ffprobe_metadata", lambda _path: {"width": 1920, "height": 1080, "duration_seconds": 240, "fps": 30})

    response = client.post(f"/api/quality/renders/{rendered_id}", json={"platforms": ["youtube_shorts"]})

    assert response.status_code == 200
    report = response.json()["reports"][0]
    assert report["passed"] is False
    assert any(issue["severity"] == "error" for issue in report["issues"])
    assert response.json()["package_ready"] is False


def test_measure_audio_loudness_parses_ffmpeg_json(monkeypatch, tmp_path: Path) -> None:
    from app.services import quality

    media_path = tmp_path / "audio.mp4"
    media_path.write_bytes(b"video")

    class Completed:
        returncode = 0
        stderr = """
        frame=42
        {
          "input_i" : "-13.87",
          "input_tp" : "-1.42",
          "input_lra" : "3.20",
          "input_thresh" : "-24.11"
        }
        """

    monkeypatch.setattr(quality, "ensure_ffmpeg", lambda: None)
    monkeypatch.setattr(quality.subprocess, "run", lambda *args, **kwargs: Completed())

    result = quality.measure_audio_loudness(media_path)

    assert result["status"] == "measured"
    assert result["integrated_lufs"] == -13.87
    assert result["true_peak_dbtp"] == -1.42
    assert result["loudness_range_lu"] == 3.2


def test_measure_audio_loudness_detects_silence(monkeypatch, tmp_path: Path) -> None:
    from app.services import quality

    media_path = tmp_path / "silent.mp4"
    media_path.write_bytes(b"video")

    class Completed:
        returncode = 0
        stderr = """
        {
          "input_i" : "-inf",
          "input_tp" : "-inf",
          "input_lra" : "0.00",
          "input_thresh" : "-70.00"
        }
        """

    monkeypatch.setattr(quality, "ensure_ffmpeg", lambda: None)
    monkeypatch.setattr(quality.subprocess, "run", lambda *args, **kwargs: Completed())

    result = quality.measure_audio_loudness(media_path)

    assert result["status"] == "silent"
    assert result["integrated_lufs"] is None
    assert result["true_peak_dbtp"] is None
    issues = quality.audio_quality_issues({"loudness": result})
    assert issues[0]["code"] == "audio_silence"
    assert issues[0]["severity"] == "error"
    issues = quality.audio_quality_issues({"loudness": result})
    assert issues[0]["code"] == "audio_silence"
    assert issues[0]["severity"] == "error"


def test_quality_check_reuses_persistent_analysis_cache(monkeypatch) -> None:
    from app.services import quality

    rendered_id = create_render(1080, 1920, 24, status="approved")
    calls = {"probe": 0, "loudness": 0}

    def fake_probe(_path):
        calls["probe"] += 1
        return {
            "width": 1080,
            "height": 1920,
            "duration_seconds": 24,
            "fps": 30,
            "has_audio": True,
        }

    def fake_loudness(_path):
        calls["loudness"] += 1
        return {"status": "measured", "integrated_lufs": -14.0, "true_peak_dbtp": -2.0}

    monkeypatch.setattr(quality, "ffprobe_metadata", fake_probe)
    monkeypatch.setattr(quality, "measure_audio_loudness", fake_loudness)

    first = client.post(f"/api/quality/renders/{rendered_id}", json={"platforms": ["tiktok"]})
    second = client.post(f"/api/quality/renders/{rendered_id}", json={"platforms": ["tiktok"]})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["analysis_cache"]["status"] == "miss"
    assert second.json()["analysis_cache"]["status"] == "hit"
    assert calls == {"probe": 1, "loudness": 1}
    with SessionLocal() as db:
        rendered = db.get(RenderedVideo, rendered_id)
        assert rendered is not None
        assert rendered.quality_cache_json


def test_quality_cache_invalidates_when_render_file_changes(monkeypatch) -> None:
    from app.services import quality

    rendered_id = create_render(1080, 1920, 24, status="approved")
    calls = 0

    def fake_probe(_path):
        nonlocal calls
        calls += 1
        return {"width": 1080, "height": 1920, "duration_seconds": 24, "fps": 30, "has_audio": False}

    monkeypatch.setattr(quality, "ffprobe_metadata", fake_probe)

    first = client.post(f"/api/quality/renders/{rendered_id}", json={"platforms": ["tiktok"]})
    with SessionLocal() as db:
        rendered = db.get(RenderedVideo, rendered_id)
        assert rendered is not None
        Path(rendered.path).write_bytes(b"render changed after first analysis")
    second = client.post(f"/api/quality/renders/{rendered_id}", json={"platforms": ["tiktok"]})

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["analysis_cache"]["status"] == "miss"
    assert calls == 2


def test_quality_check_blocks_silent_or_clipping_audio(monkeypatch) -> None:
    from app.services import quality

    rendered_id = create_render(1080, 1920, 24, status="approved")
    monkeypatch.setattr(
        quality,
        "ffprobe_metadata",
        lambda _path: {"width": 1080, "height": 1920, "duration_seconds": 24, "fps": 30, "has_audio": True},
    )
    monkeypatch.setattr(
        quality,
        "measure_audio_loudness",
        lambda _path: {"status": "measured", "integrated_lufs": -14.0, "true_peak_dbtp": 0.2},
    )

    response = client.post(f"/api/quality/renders/{rendered_id}", json={"platforms": ["tiktok"]})

    assert response.status_code == 200
    payload = response.json()
    assert payload["package_ready"] is False
    assert any(item["code"] == "audio_clipping" and item["severity"] == "error" for item in payload["audio_issues"])
    assert any("clipping" in item["message"].lower() for item in payload["reports"][0]["issues"])


def test_ffprobe_metadata_includes_codec_audio_and_container(monkeypatch, tmp_path: Path) -> None:
    from app.services import media

    media_path = tmp_path / "probe.mp4"
    media_path.write_bytes(b"video")

    class Completed:
        stdout = """
        {
          "streams": [
            {
              "codec_type": "video",
              "codec_name": "h264",
              "width": 1920,
              "height": 1080,
              "avg_frame_rate": "30000/1001",
              "duration": "12.5"
            },
            {
              "codec_type": "audio",
              "codec_name": "aac",
              "sample_rate": "48000",
              "channels": 2
            }
          ],
          "format": {
            "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
            "duration": "12.5",
            "bit_rate": "4200000"
          }
        }
        """

    monkeypatch.setattr(media, "ensure_ffmpeg", lambda: None)
    monkeypatch.setattr(media.subprocess, "run", lambda *args, **kwargs: Completed())

    result = media.ffprobe_metadata(media_path)

    assert result["video_codec"] == "h264"
    assert result["audio_codec"] == "aac"
    assert result["audio_sample_rate_hz"] == 48_000
    assert result["audio_channels"] == 2
    assert result["has_audio"] is True
    assert result["container_format"].startswith("mov,mp4")
    assert result["format_bit_rate_kbps"] == 4200.0


def test_quality_check_batch_endpoint_and_service(monkeypatch) -> None:
    from app.services import quality

    monkeypatch.setattr(quality, "analyze_render", lambda db, rendered: (
        {
            "width": 1080,
            "height": 1920,
            "aspect_ratio": 0.5625,
            "orientation": "vertical",
            "duration_seconds": 15.0,
            "size_bytes": 5_000_000,
            "fps": 30.0,
            "video_codec": "h264",
            "audio_codec": "aac",
            "has_audio": True,
            "audio_sample_rate_hz": 48000,
            "audio_channels": 2,
            "integrated_loudness_lufs": -14.2,
            "true_peak_dbfs": -1.5,
            "loudness_range_lu": 6.5,
            "max_volume_db": -1.5,
            "mean_volume_db": -18.0,
            "silence_detected": False,
            "silence_duration_seconds": 0.0,
            "clipping_detected": False,
        },
        {"source": "test", "cached": False, "saved_to_db": False},
    ))

    video_path = DATA_ROOT / "renders" / f"{uuid4().hex}.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.write_bytes(b"0" * 1000)

    with SessionLocal() as db:
        asset = Asset(
            original_path=str(video_path),
            stored_path=str(video_path),
            filename="batch_test.mp4",
            sha256=uuid4().hex + uuid4().hex,
            size_bytes=1000,
            duration_seconds=15.0,
            width=1080,
            height=1920,
            fps=30,
            orientation="vertical",
            metadata_status="ready",
        )
        template = Template(name=f"Tpl {uuid4().hex[:6]}", description="", recipe_json=DEFAULT_RECIPE.__repr__())
        db.add(asset)
        db.add(template)
        db.flush()
        batch = Batch(name=f"Lote QC {uuid4().hex[:6]}", template_id=template.id, total_jobs=2)
        db.add(batch)
        db.flush()
        job1 = RenderJob(batch_id=batch.id, asset_id=asset.id, template_id=template.id, status="completed")
        job2 = RenderJob(batch_id=batch.id, asset_id=asset.id, template_id=template.id, status="completed")
        db.add(job1)
        db.add(job2)
        db.flush()
        rendered1 = RenderedVideo(job_id=job1.id, asset_id=asset.id, template_id=template.id, path=str(video_path), duration_seconds=15.0, width=1080, height=1920, status="approved")
        rendered2 = RenderedVideo(job_id=job2.id, asset_id=asset.id, template_id=template.id, path=str(video_path), duration_seconds=15.0, width=1080, height=1920, status="approved")
        db.add(rendered1)
        db.add(rendered2)
        db.commit()
        batch_id = batch.id

    response = client.post(f"/api/quality/batches/{batch_id}", json={"platforms": ["instagram_reels", "tiktok"]})
    assert response.status_code == 200
    data = response.json()
    assert data["batch_id"] == batch_id
    assert data["total_renders"] == 2
    assert data["passed_count"] == 2
    assert data["pass_rate"] == 100.0
    assert len(data["items"]) == 2

    summary_response = client.get(f"/api/quality/batches/{batch_id}")
    assert summary_response.status_code == 200
    assert summary_response.json()["batch_id"] == batch_id

