from __future__ import annotations

from uuid import uuid4
from pathlib import Path
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Asset, Transcript
from conftest import DATA_ROOT

client = TestClient(app)


def test_transcription_status_endpoint() -> None:
    response = client.get("/api/transcriptions/status")
    assert response.status_code == 200
    data = response.json()
    assert "available" in data
    assert "engine" in data
    assert "model" in data


def test_transcribe_asset_and_export_subtitles(monkeypatch) -> None:
    from app.routes import transcriptions

    monkeypatch.setattr(transcriptions, "transcribe_asset", lambda asset, language: {
        "asset_id": asset.id,
        "engine": "faster-whisper",
        "path": "data/transcripts/test.txt",
        "text": "Ola mundo dos shorts.",
        "segments": [
            {"start": 0.0, "end": 2.5, "text": "Ola mundo"},
            {"start": 2.5, "end": 5.0, "text": "dos shorts."},
        ],
        "words": [
            {"word": "Ola", "start": 0.0, "end": 1.0, "probability": 0.99},
            {"word": "mundo", "start": 1.0, "end": 2.5, "probability": 0.98},
            {"word": "dos", "start": 2.5, "end": 3.2, "probability": 0.95},
            {"word": "shorts.", "start": 3.2, "end": 5.0, "probability": 0.97},
        ],
    })

    video_path = DATA_ROOT / "assets" / f"{uuid4().hex}.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.write_bytes(b"0" * 1000)

    with SessionLocal() as db:
        asset = Asset(
            original_path=str(video_path),
            stored_path=str(video_path),
            filename="speech_test.mp4",
            sha256=uuid4().hex + uuid4().hex,
            size_bytes=1000,
            duration_seconds=5.0,
            width=1080,
            height=1920,
            fps=30,
            orientation="vertical",
            metadata_status="ready",
        )
        db.add(asset)
        db.commit()
        asset_id = asset.id

    # 1. Create transcription
    response = client.post("/api/transcriptions", json={"asset_id": asset_id, "language": "pt"})
    assert response.status_code == 200
    data = response.json()
    transcript_id = data["transcript_id"]
    assert transcript_id is not None

    # 2. Get transcript details
    get_res = client.get(f"/api/transcriptions/{transcript_id}")
    assert get_res.status_code == 200
    t_data = get_res.json()
    assert t_data["engine"] == "faster-whisper"
    assert len(t_data["segments"]) == 2
    assert len(t_data["words"]) == 4

    # 3. Patch transcript
    patch_res = client.patch(
        f"/api/transcriptions/{transcript_id}",
        json={"text": "Texto editado", "segments": [{"start": 0.0, "end": 5.0, "text": "Texto editado"}]},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["text"] == "Texto editado"
    assert len(patch_res.json()["segments"]) == 1

    # 4. Export SRT
    srt_res = client.get(f"/api/transcriptions/{transcript_id}/subtitles?format=srt")
    assert srt_res.status_code == 200
    assert "00:00:00,000 --> 00:00:05,000" in srt_res.text
    assert "Texto editado" in srt_res.text

    # 5. Export VTT
    vtt_res = client.get(f"/api/transcriptions/{transcript_id}/subtitles?format=vtt")
    assert vtt_res.status_code == 200
    assert "WEBVTT" in vtt_res.text
    assert "00:00:00.000 --> 00:00:05.000" in vtt_res.text

    # 6. Export ASS Karaoke
    ass_res = client.get(f"/api/transcriptions/{transcript_id}/subtitles?format=ass")
    assert ass_res.status_code == 200
    assert "[Script Info]" in ass_res.text
    assert "Style: Karaoke" in ass_res.text
    assert "Dialogue:" in ass_res.text

