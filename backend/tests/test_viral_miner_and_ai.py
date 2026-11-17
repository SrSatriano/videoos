from __future__ import annotations

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Asset, Template


def test_ai_status_endpoint():
    client = TestClient(app)
    response = client.get("/api/system/ai-status")
    assert response.status_code == 200
    data = response.json()
    assert "google" in data
    assert "ollama" in data
    assert "tts" in data
    assert "whisper" in data
    assert data["tts"]["engine"] == "Edge-TTS (Neural)"


def test_google_api_test_endpoint_without_key():
    client = TestClient(app)
    response = client.post("/api/system/test-google-api", json={"api_key": ""})
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is False
    assert "Nenhuma chave" in data["error"]


def test_tts_voices_and_synthesize():
    client = TestClient(app)
    voices_resp = client.get("/api/system/tts/voices")
    assert voices_resp.status_code == 200
    voices = voices_resp.json()
    assert len(voices) >= 3
    assert any(v["id"] == "pt-BR-AntonioNeural" for v in voices)

    synth_resp = client.post("/api/system/tts/synthesize", json={
        "text": "Teste de automação com inteligência artificial.",
        "voice": "pt-BR-AntonioNeural",
    })
    assert synth_resp.status_code == 200
    res = synth_resp.json()
    assert "audio_path" in res
    assert res["char_count"] > 0


def test_mine_viral_clips_and_create_batch():
    client = TestClient(app)
    db = SessionLocal()
    try:
        # Criar asset de teste
        asset = Asset(
            filename="video_teste.mp4",
            original_path="/workspace/data/assets/video_teste.mp4",
            stored_path="/workspace/data/assets/video_teste.mp4",
            sha256="testsha256viral1234567890abcdef",
            size_bytes=1024,
            duration_seconds=120.0,
        )
        db.add(asset)
        
        # Criar template de teste
        template = Template(
            name="Template 9:16 Viral",
            description="Teste",
            recipe_json='{"canvas": {"width": 1080, "height": 1920}, "text_layers": [{"type": "headline", "text": "TITULO"}]}',
        )
        db.add(template)
        db.commit()
        db.refresh(asset)
        db.refresh(template)

        # 1. Minerar cortes virais
        mine_resp = client.post(f"/api/clips/assets/{asset.id}/mine-viral", json={
            "min_seconds": 15,
            "max_seconds": 45,
            "target_count": 3,
        })
        assert mine_resp.status_code == 200
        data = mine_resp.json()
        assert data["asset_id"] == asset.id
        assert "clips" in data
        assert len(data["clips"]) > 0

        first_clip = data["clips"][0]
        assert 0 <= first_clip["viral_score"] <= 100
        assert first_clip["duration"] >= 10.0
        assert len(first_clip["hook"]) > 0

        # 2. Criar lote de renderização a partir dos cortes minerados
        batch_resp = client.post("/api/clips/batch-create", json={
            "asset_id": asset.id,
            "template_id": template.id,
            "clips": data["clips"][:2],
            "batch_name": "Lote Cortes Automatizados",
        })
        assert batch_resp.status_code == 200
        batch_data = batch_resp.json()
        assert batch_data["name"] == "Lote Cortes Automatizados"
        assert batch_data["total_jobs"] == 2
    finally:
        db.close()
