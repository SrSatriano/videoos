from __future__ import annotations

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Asset, Batch, RenderJob, Template


client = TestClient(app)


def _make_asset(db, asset_id: str, sha: str) -> Asset:
    asset = Asset(
        id=asset_id,
        original_path=f"D:/x/{asset_id}.mp4",
        stored_path=f"D:/x/{asset_id}.mp4",
        filename=f"{asset_id}.mp4",
        sha256=sha,
        size_bytes=1,
        orientation="unknown",
        metadata_status="ready",
    )
    db.add(asset)
    return asset


def test_delete_removes_asset_from_library() -> None:
    asset_id = "de1e7e00" + "0" * 24
    with SessionLocal() as db:
        _make_asset(db, asset_id, "e" * 64)
        db.commit()

    listed = client.get("/api/assets").json()
    assert any(item["id"] == asset_id for item in listed)

    response = client.delete(f"/api/assets/{asset_id}")
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 1

    listed_after = client.get("/api/assets").json()
    assert not any(item["id"] == asset_id for item in listed_after)


def test_delete_missing_asset_returns_404() -> None:
    response = client.delete("/api/assets/" + "f" * 32)
    assert response.status_code == 404


def test_delete_blocks_asset_in_use_by_render_job() -> None:
    asset_id = "9" * 32
    with SessionLocal() as db:
        template = Template(name="T", description="", recipe_json="{}")
        db.add(template)
        db.flush()
        batch = Batch(name="B", template_id=template.id, total_jobs=1)
        db.add(batch)
        db.flush()
        _make_asset(db, asset_id, "a1" + "b" * 62)
        db.add(RenderJob(batch_id=batch.id, asset_id=asset_id, template_id=template.id))
        db.commit()

    response = client.delete(f"/api/assets/{asset_id}")
    assert response.status_code == 409  # bloqueado: em uso

    # Continua na biblioteca.
    listed = client.get("/api/assets").json()
    assert any(item["id"] == asset_id for item in listed)


def test_bulk_delete_reports_deleted_and_skipped() -> None:
    ok_id = "b" * 32
    used_id = "7" * 32
    with SessionLocal() as db:
        template = Template(name="T2", description="", recipe_json="{}")
        db.add(template)
        db.flush()
        batch = Batch(name="B2", template_id=template.id, total_jobs=1)
        db.add(batch)
        db.flush()
        _make_asset(db, ok_id, "c1" + "c" * 62)
        _make_asset(db, used_id, "d1" + "d" * 62)
        db.add(RenderJob(batch_id=batch.id, asset_id=used_id, template_id=template.id))
        db.commit()

    response = client.post("/api/assets/delete", json={"asset_ids": [ok_id, used_id, "0" * 32]})
    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload["deleted"]] == [ok_id]
    assert [item["id"] for item in payload["skipped"]] == [used_id]
    assert payload["missing"] == ["0" * 32]
