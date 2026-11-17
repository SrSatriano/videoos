from __future__ import annotations

import json
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Asset, Template, Batch, RenderJob


def test_script_to_video_generation():
    client = TestClient(app)
    resp = client.post("/api/agents/script-to-video", json={"topic": "5 Hábitos de Alta Produtividade"})
    assert resp.status_code == 200
    data = resp.json()
    assert "title" in data
    assert "blocks" in data
    assert len(data["blocks"]) >= 4
    assert "full_narration" in data
    assert len(data["full_narration"]) > 20
    
    first_block = data["blocks"][0]
    assert "block_name" in first_block
    assert "spoken_text" in first_block
    assert "visual_direction" in first_block
    assert "visual_prompt" in first_block


def test_batch_create_conditional_editing_flags():
    client = TestClient(app)
    db = SessionLocal()
    try:
        asset = Asset(
            filename="cond_edit_video.mp4",
            original_path="/workspace/data/assets/cond_edit_video.mp4",
            stored_path="/workspace/data/assets/cond_edit_video.mp4",
            sha256="condeditsha256_1234567890abcdef",
            size_bytes=2048,
            duration_seconds=60.0,
        )
        db.add(asset)

        template = Template(
            name="Template Base Condicional",
            description="Teste",
            recipe_json='{"canvas": {"width": 1080, "height": 1920}}',
        )
        db.add(template)
        db.commit()
        db.refresh(asset)
        db.refresh(template)

        clips_payload = [
            {
                "start_seconds": 0.0,
                "end_seconds": 15.0,
                "duration": 15.0,
                "suggested_title": "Corte Condicional 1",
                "viral_score": 85,
                "hook": "Gancho matador",
                "virality_rationale": "Alto ritmo",
                "suggested_copy": "Copy viral",
                "suggested_hashtags": ["#viral"],
            }
        ]

        batch_resp = client.post("/api/clips/batch-create", json={
            "asset_id": asset.id,
            "template_id": template.id,
            "clips": clips_payload,
            "batch_name": "Lote com Edicao Condicional",
            "enable_captions": True,
            "caption_style": "neon",
            "enable_music": True,
            "music_volume": 0.22,
            "enable_jumpcut": True,
        })
        assert batch_resp.status_code == 200
        batch_data = batch_resp.json()
        assert batch_data["name"] == "Lote com Edicao Condicional"

        # Verificar se a receita do template derivado do job gravou as diretrizes condicionais
        batch_obj = db.get(Batch, batch_data["id"])
        assert batch_obj is not None
        job_obj = db.query(RenderJob).filter(RenderJob.batch_id == batch_obj.id).first()
        assert job_obj is not None
        derived_tpl = db.get(Template, job_obj.template_id)
        assert derived_tpl is not None

        recipe = json.loads(derived_tpl.recipe_json)
        assert "captions" in recipe
        assert recipe["captions"]["style"] == "neon"
        assert "audio_ducking" in recipe
        assert recipe["audio_ducking"]["music_volume"] == 0.22
        assert "jump_cut" in recipe
        assert recipe["jump_cut"]["enabled"] is True

    finally:
        db.close()


def test_generate_faceless_video_flow():
    client = TestClient(app)
    db = SessionLocal()
    try:
        resp = client.post("/api/agents/generate-faceless-video", json={
            "topic": "Curiosidades sobre o Universo",
            "voice": "pt-BR-AntonioNeural",
            "enable_captions": True,
            "caption_style": "hormozi",
            "video_name": "Vídeo Universo IA",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "batch_id" in data
        assert "job_id" in data
        assert "tts" in data
        assert "audio_path" in data["tts"]
        assert "audio_url" in data["tts"]
        assert data["tts"]["audio_url"].startswith("/media/tts/")

        # Verificar se o Batch e Job existem no banco de dados
        batch = db.get(Batch, data["batch_id"])
        assert batch is not None
        assert "Faceless IA" in batch.name

        job = db.get(RenderJob, data["job_id"])
        assert job is not None
        assert job.status == "queued"
        assert job.batch_id == batch.id

    finally:
        db.close()
