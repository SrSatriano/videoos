from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Asset

from conftest import DATA_ROOT


client = TestClient(app)


def create_asset(filename: str = "editor-tool.mp4") -> str:
    stored_path = DATA_ROOT / "assets" / filename
    stored_path.parent.mkdir(parents=True, exist_ok=True)
    stored_path.write_bytes(b"fake video")
    with SessionLocal() as db:
        asset = Asset(
            original_path=str(stored_path),
            stored_path=str(stored_path),
            filename=filename,
            sha256=uuid4().hex + uuid4().hex,
            size_bytes=stored_path.stat().st_size,
            duration_seconds=12.0,
            width=1080,
            height=1920,
            fps=30,
            orientation="vertical",
            metadata_status="ready",
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return asset.id


def test_export_presets_endpoint() -> None:
    response = client.get("/api/editor/export-presets")

    assert response.status_code == 200
    preset_ids = {preset["id"] for preset in response.json()}
    assert {"preview_fast", "shorts_quality", "archive_master", "light_upload"}.issubset(preset_ids)


def test_manual_marker_crud() -> None:
    asset_id = create_asset("manual-marker.mp4")

    created = client.post(
        f"/api/editor/assets/{asset_id}/markers",
        json={
            "time_seconds": 3.5,
            "label": "Hook forte",
            "marker_type": "hook",
            "color": "#51d88a",
            "notes": "Teste",
        },
    )
    listed = client.get(f"/api/editor/assets/{asset_id}/markers")

    assert created.status_code == 200
    assert created.json()["label"] == "Hook forte"
    assert listed.status_code == 200
    assert listed.json()[0]["time_seconds"] == 3.5

    deleted = client.delete(f"/api/editor/markers/{created.json()['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/api/editor/assets/{asset_id}/markers").json() == []


def test_scene_detection_stores_auto_markers(monkeypatch) -> None:
    from app.services import editor_tools

    asset_id = create_asset("scene-detect.mp4")

    def fake_run(*_args, **_kwargs):
        return SimpleNamespace(stderr="showinfo pts_time:0.10\nshowinfo pts_time:1.25\nshowinfo pts_time:2.75\n")

    monkeypatch.setattr(editor_tools, "ensure_ffmpeg", lambda: None)
    monkeypatch.setattr(editor_tools.subprocess, "run", fake_run)

    response = client.post(f"/api/editor/assets/{asset_id}/scene-detect", json={"threshold": 0.3, "limit": 10})

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert [marker["label"] for marker in payload["markers"]] == ["Cena 01", "Cena 02"]


def test_proxy_generation_records_proxy(monkeypatch) -> None:
    from app.services import editor_tools

    asset_id = create_asset("proxy-source.mp4")

    def fake_run(args, *_unused_args, **_kwargs):
        target = args[-1]
        DATA_ROOT.joinpath("proxies").mkdir(parents=True, exist_ok=True)
        from pathlib import Path

        Path(target).write_bytes(b"proxy")
        return SimpleNamespace(stderr="")

    monkeypatch.setattr(editor_tools, "ensure_ffmpeg", lambda: None)
    monkeypatch.setattr(editor_tools, "ffprobe_metadata", lambda _path: {"width": 720, "height": 1280})
    monkeypatch.setattr(editor_tools.subprocess, "run", fake_run)

    response = client.post(f"/api/editor/assets/{asset_id}/proxy")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["width"] == 720
    assert payload["media_url"].endswith(".mp4")
