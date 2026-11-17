from __future__ import annotations

import json
from pathlib import Path
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Asset, Batch, RenderJob, Template


def test_generate_scene_image_service_and_endpoint():
    client = TestClient(app)
    db = SessionLocal()
    try:
        resp = client.post("/api/agents/generate-scene-image", json={
            "prompt": "Futuristic cyberpunk neon city with flying vehicles 8k photorealistic",
            "aspect_ratio": "9:16",
            "save_as_asset": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "image_path" in data
        assert "image_url" in data
        assert data["image_url"].startswith("/media/broll/")
        assert data["width"] == 1080
        assert data["height"] == 1920
        assert data["asset_id"] is not None

        # Verificar se o arquivo existe fisicamente
        img_path = Path(data["image_path"])
        assert img_path.exists()
        assert img_path.stat().st_size > 0

        # Verificar se o Asset foi registrado no banco
        asset_obj = db.get(Asset, data["asset_id"])
        assert asset_obj is not None
        assert asset_obj.filename == data["filename"]
        assert asset_obj.orientation == "portrait"
    finally:
        db.close()


def test_autopilot_pipeline_execution():
    client = TestClient(app)
    db = SessionLocal()
    try:
        asset = Asset(
            filename="podcast_entrevista.mp4",
            original_path="/workspace/data/assets/podcast_entrevista.mp4",
            stored_path="/workspace/data/assets/podcast_entrevista.mp4",
            sha256="autopilotsha256_0987654321fedcba",
            size_bytes=4096,
            duration_seconds=180.0,
            width=1920,
            height=1080,
            orientation="landscape",
        )
        db.add(asset)

        template = Template(
            name="Template 9:16 Autopilot Base",
            description="Base",
            recipe_json='{"canvas": {"width": 1080, "height": 1920}}',
        )
        db.add(template)
        db.commit()
        db.refresh(asset)
        db.refresh(template)

        # Executar Piloto Automático Ponta a Ponta
        resp = client.post("/api/clips/autopilot", json={
            "asset_id": asset.id,
            "min_score": 60,
            "max_clips": 2,
            "enable_captions": True,
            "caption_style": "minimal",
            "enable_music": True,
            "music_volume": 0.25,
            "enable_jumpcut": True,
            "batch_name": "Lote Piloto Automático Oficial",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "batch_id" in data
        assert data["batch_name"] == "Lote Piloto Automático Oficial"
        assert data["total_jobs"] >= 1
        assert data["clips_selected"] >= 1
        assert len(data["clips"]) >= 1

        # Verificar integridade do lote no banco
        batch = db.get(Batch, data["batch_id"])
        assert batch is not None
        assert batch.total_jobs == data["total_jobs"]

        # Verificar jobs e receitas derivadas
        jobs = db.query(RenderJob).filter(RenderJob.batch_id == batch.id).all()
        assert len(jobs) == data["total_jobs"]
        for j in jobs:
            assert j.status == "queued"
            job_tpl = db.get(Template, j.template_id)
            assert job_tpl is not None
            recipe = json.loads(job_tpl.recipe_json)
            assert "captions" in recipe
            assert recipe["captions"]["style"] == "minimal"
            assert "audio_ducking" in recipe
            assert recipe["audio_ducking"]["music_volume"] == 0.25
            assert "jump_cut" in recipe
            assert recipe["jump_cut"]["enabled"] is True

    finally:
        db.close()
