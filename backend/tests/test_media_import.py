from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import IMPORT_ROOTS
from app.database import SessionLocal
from app.main import app
from app.models import Asset
from app.services import media
from app.services.media import path_is_allowed, sha256_file


client = TestClient(app)


def test_path_with_accent_is_allowed() -> None:
    root = IMPORT_ROOTS[0]
    video_path = root / "vídeo teste.mp4"
    video_path.write_bytes(b"fake video")

    assert path_is_allowed(video_path)


def test_rotation_metadata_swaps_display_dimensions() -> None:
    width, height = media.display_dimensions(1920, 1080, media.rotation_for({"tags": {"rotate": "90"}}))

    assert width == 1080
    assert height == 1920
    assert media.orientation_for(width, height) == "vertical"


def test_import_detects_duplicate_by_hash() -> None:
    root = IMPORT_ROOTS[0]
    video_path = root / "duplicado.mp4"
    video_path.write_bytes(b"same bytes")

    first = client.post("/api/assets/import", json={"paths": [str(video_path)], "copy_to_library": True})
    second = client.post("/api/assets/import", json={"paths": [str(video_path)], "copy_to_library": True})

    assert first.status_code == 200
    assert second.status_code == 200
    first_asset = first.json()["imported"][0]
    second_asset = second.json()["imported"][0]
    assert first_asset["id"] == second_asset["id"]
    assert first_asset["sha256"] == sha256_file(video_path)
    assert first_asset["metadata_status"] in {"ffmpeg_missing", "metadata_failed", "ready"}


def test_import_success_generates_thumbnail_with_metadata(monkeypatch) -> None:
    root = IMPORT_ROOTS[0]
    video_path = root / "metadata-ready.mp4"
    video_path.write_bytes(b"metadata ready bytes")

    monkeypatch.setattr(
        media,
        "ffprobe_metadata",
        lambda _path: {
            "duration_seconds": 10.0,
            "width": 1080,
            "height": 1920,
            "fps": 30.0,
            "orientation": "vertical",
        },
    )

    def fake_thumbnail(_input_path: Path, output_path: Path, at_seconds: float | None = None) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"jpg")

    monkeypatch.setattr(media, "generate_thumbnail", fake_thumbnail)

    response = client.post("/api/assets/import", json={"paths": [str(video_path)], "copy_to_library": True})
    asset = response.json()["imported"][0]

    assert response.status_code == 200
    assert asset["metadata_status"] == "ready"
    assert asset["thumbnail_url"]
    assert asset["orientation"] == "vertical"


def test_import_rejects_path_outside_allowed_roots_when_restricted(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(media, "ALLOW_ANY_IMPORT_PATH", False)
    outside = tmp_path / "outside.mp4"
    outside.write_bytes(b"x")

    response = client.post("/api/assets/import", json={"paths": [str(outside)], "copy_to_library": True})

    assert response.status_code == 400


def test_upload_endpoint_imports_from_explorer() -> None:
    response = client.post(
        "/api/assets/upload",
        files=[("files", ("explorer-video.mp4", b"fake explorer bytes", "video/mp4"))],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["imported"][0]["filename"] == "explorer-video.mp4"


def test_reindex_repairs_existing_asset_metadata(monkeypatch) -> None:
    asset_id = "a" * 32
    canonical_path = media.ASSETS_DIR / f"{asset_id}.mp4"
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    canonical_path.write_bytes(b"video bytes")

    with SessionLocal() as db:
        db.add(
            Asset(
                id=asset_id,
                original_path="D:/old/video.mp4",
                stored_path="D:/old/video.mp4",
                filename="video.mp4",
                sha256="b" * 64,
                size_bytes=0,
                duration_seconds=None,
                width=None,
                height=None,
                fps=None,
                orientation="unknown",
                thumbnail_path=None,
                metadata_status="metadata_failed",
            )
        )
        db.commit()

    monkeypatch.setattr(
        media,
        "ffprobe_metadata",
        lambda _path: {
            "duration_seconds": 54.0,
            "width": 720,
            "height": 1280,
            "fps": 30.0,
            "orientation": "vertical",
        },
    )

    def fake_thumbnail(_input_path: Path, output_path: Path, at_seconds: float | None = None) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"thumb")

    monkeypatch.setattr(media, "generate_thumbnail", fake_thumbnail)

    response = client.post(f"/api/assets/{asset_id}/reindex")

    assert response.status_code == 200
    payload = response.json()
    assert payload["asset"]["stored_path"] == str(canonical_path)
    assert payload["asset"]["metadata_status"] == "ready"
    assert payload["asset"]["media_url"].endswith(f"/assets/{asset_id}.mp4")
    assert payload["asset"]["thumbnail_url"].endswith(f"/thumbnails/assets/{asset_id}.jpg")


def test_bulk_reindex_skips_ready_assets(monkeypatch) -> None:
    asset_id = "c" * 32
    canonical_path = media.ASSETS_DIR / f"{asset_id}.mp4"
    thumbnail_path = media.THUMBNAILS_DIR / "assets" / f"{asset_id}.jpg"
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
    canonical_path.write_bytes(b"video bytes")
    thumbnail_path.write_bytes(b"thumb")

    with SessionLocal() as db:
        db.add(
            Asset(
                id=asset_id,
                original_path=str(canonical_path),
                stored_path=str(canonical_path),
                filename="ready.mp4",
                sha256="d" * 64,
                size_bytes=canonical_path.stat().st_size,
                duration_seconds=54.0,
                width=720,
                height=1280,
                fps=30.0,
                orientation="vertical",
                thumbnail_path=str(thumbnail_path),
                metadata_status="ready",
            )
        )
        db.commit()

    monkeypatch.setattr(media, "ffprobe_metadata", lambda _path: {})
    response = client.post("/api/assets/reindex")

    assert response.status_code == 200
    payload = response.json()
    assert payload["skipped"] >= 1
