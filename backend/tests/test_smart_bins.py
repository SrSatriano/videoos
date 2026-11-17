from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Asset, AssetProxy

from conftest import DATA_ROOT


client = TestClient(app)


def create_asset(filename: str, *, orientation: str, duration: float | None, metadata_status: str = "ready", thumbnail: bool = True) -> str:
    stored_path = DATA_ROOT / "assets" / filename
    stored_path.parent.mkdir(parents=True, exist_ok=True)
    stored_path.write_bytes(b"asset")
    thumbnail_path = DATA_ROOT / "thumbnails" / f"{filename}.jpg"
    if thumbnail:
        thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
        thumbnail_path.write_bytes(b"thumb")
    with SessionLocal() as db:
        asset = Asset(
            original_path=str(stored_path),
            stored_path=str(stored_path),
            filename=filename,
            sha256=uuid4().hex + uuid4().hex,
            size_bytes=stored_path.stat().st_size,
            duration_seconds=duration,
            width=1080 if orientation == "vertical" else 1920,
            height=1920 if orientation == "vertical" else 1080,
            fps=30,
            orientation=orientation,
            thumbnail_path=str(thumbnail_path) if thumbnail else None,
            metadata_status=metadata_status,
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return asset.id


def test_smart_bins_group_assets_by_status_and_shape() -> None:
    vertical_id = create_asset("vertical.mp4", orientation="vertical", duration=54)
    long_id = create_asset("long.mp4", orientation="vertical", duration=240)
    attention_id = create_asset("attention.mp4", orientation="horizontal", duration=None, metadata_status="metadata_failed", thumbnail=False)
    with SessionLocal() as db:
        db.add(AssetProxy(asset_id=vertical_id, path=str(DATA_ROOT / "proxies" / "vertical.mp4"), status="ready"))
        db.commit()

    response = client.get("/api/assets/smart-bins")

    assert response.status_code == 200
    bins = {item["id"]: item for item in response.json()["bins"]}
    assert vertical_id in bins["shorts_ready"]["asset_ids"]
    assert vertical_id in bins["under_60"]["asset_ids"]
    assert vertical_id in bins["has_proxy"]["asset_ids"]
    assert long_id in bins["long_form"]["asset_ids"]
    assert attention_id in bins["needs_attention"]["asset_ids"]
