from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.seed import normalize_renderable_recipe

client = TestClient(app)


def test_preset_library_has_requested_counts():
    response = client.get("/api/preset-library")
    payload = response.json()

    assert response.status_code == 200
    assert payload["counts"]["templates"] >= 50
    assert payload["counts"]["filters"] >= 100
    assert payload["counts"]["masks"] >= 100
    assert payload["counts"]["captions"] >= 50


def test_can_install_template_preset():
    response = client.post("/api/preset-library/templates/template-01/install")

    assert response.status_code == 200
    assert response.json()["name"].startswith("Template Massa 01")


def test_template_presets_only_advertise_rendered_features():
    response = client.get("/api/preset-library")
    templates = response.json()["templates"]

    assert response.status_code == 200
    for template in templates:
        recipe = template["recipe"]
        assert "layout" not in recipe
        assert "music" not in recipe
        assert "intro" not in recipe
        assert "outro" not in recipe
        assert "cta" not in recipe
        assert recipe["format"]["fit"] in {"crop", "contain"}
        assert recipe.get("captions", {}).get("enabled") is False


def test_legacy_recipe_normalization_removes_unsupported_fields():
    recipe = {
        "format": {"width": 1080, "height": 1920, "fit": "crop", "fps": 30},
        "captions": {"enabled": True, "burned_srt_path": "/workspace/data/captions/test.srt", "style": "karaoke"},
        "cta": {"enabled": True, "text": "Comenta"},
        "music": {"track_id": "unused"},
    }

    normalized = normalize_renderable_recipe(recipe)

    assert "cta" not in normalized
    assert "music" not in normalized
    assert "style" not in normalized["captions"]
    assert normalized["captions"]["enabled"] is True
    assert normalized["captions"]["burned_srt_path"] == "/workspace/data/captions/test.srt"
