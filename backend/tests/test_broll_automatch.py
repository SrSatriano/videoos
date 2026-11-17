from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.broll import auto_match_broll_overlays

client = TestClient(app)


def test_auto_match_broll_overlays_function() -> None:
    segments = [
        {"start": 0.0, "end": 3.0, "text": "Hoje vamos falar sobre automacao de conteudo no computador"},
        {"start": 3.5, "end": 7.0, "text": "Depois vamos olhar os graficos de dinheiro e metricas"},
    ]
    brolls = [
        {"path": "data/assets/broll/computador.mp4", "name": "computador.mp4", "tags": ["computador", "teclado"], "duration_seconds": 5.0},
        {"path": "data/assets/broll/dinheiro.mp4", "name": "dinheiro.mp4", "tags": ["dinheiro", "graficos"], "duration_seconds": 4.0},
        {"path": "data/assets/broll/outro.mp4", "name": "outro.mp4", "tags": ["esportes"], "duration_seconds": 5.0},
    ]

    matched = auto_match_broll_overlays(segments, brolls, max_overlays=3)
    assert len(matched) == 2
    assert matched[0]["path"] == "data/assets/broll/computador.mp4"
    assert matched[0]["start"] == 0.0
    assert matched[1]["path"] == "data/assets/broll/dinheiro.mp4"
    assert matched[1]["start"] == 3.5


def test_auto_match_broll_endpoint() -> None:
    payload = {
        "segments": [{"start": 0.0, "end": 2.5, "text": "Teste de video sobre tecnologia"}],
        "available_brolls": [{"path": "broll.mp4", "name": "tecnologia", "tags": ["tecnologia"], "duration_seconds": 3.0}],
        "max_overlays": 2,
    }
    response = client.post("/api/broll/auto-match", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert len(data["overlays"]) == 1
