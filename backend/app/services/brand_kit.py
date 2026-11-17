from __future__ import annotations

from copy import deepcopy
from typing import Any

DEFAULT_BRAND_KIT: dict[str, Any] = {
    "name": "Dicas Tech",
    "colors": {"primary": "#51d88a", "accent": "#4da3ff", "text": "#ffffff", "outline": "#050607"},
    "caption": {"font_family": "Arial Bold", "font_size": 74, "position": "bottom", "keyword_color": "#ffd166"},
    "cta": {"text": "Comenta 'eu quero' para receber", "position": "final"},
    "watermark": {"enabled": True, "text": "@sistema.dark", "position": "bottom-right"},
    "layouts": ["fill", "fit", "screenshare"],
}


def normalize_brand_kit(payload: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(DEFAULT_BRAND_KIT)
    for key, value in payload.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = {**result[key], **value}
        else:
            result[key] = value
    return result
