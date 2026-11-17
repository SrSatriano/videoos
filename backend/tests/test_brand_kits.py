from __future__ import annotations

from app.services.brand_kit import normalize_brand_kit


def test_brand_kit_defaults_are_complete():
    kit = normalize_brand_kit({"name": "Dicas Tech"})
    assert kit["caption"]["font_size"] == 74
    assert kit["colors"]["primary"].startswith("#")
    assert kit["cta"]["text"]
    assert kit["name"] == "Dicas Tech"
