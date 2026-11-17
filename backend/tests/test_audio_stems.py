from __future__ import annotations

from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.services.audio_lab import demucs_status, separate_audio_stems

client = TestClient(app)


def test_demucs_status() -> None:
    status = demucs_status()
    assert "demucs_available" in status
    assert "features" in status
    assert status["dsp_available"] is True


def test_music_status_endpoint() -> None:
    response = client.get("/api/music/status")
    assert response.status_code == 200
    data = response.json()
    assert "demucs_available" in data
    assert "features" in data


def test_separate_stems_missing_file() -> None:
    response = client.post("/api/music/separate-stems", json={"audio_path": "non_existent_audio_file.wav"})
    assert response.status_code == 404
