from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ..models import BrandKit, PlatformPreset, Template
from .brand_kit import DEFAULT_BRAND_KIT
from .preset_library import template_presets
from .quality import SAFE_ZONE_GUIDES


DEFAULT_RECIPE = {
    "format": {"width": 1080, "height": 1920, "fit": "crop", "fps": 30},
    "trim": {"start": 0, "end": None},
    "text": {
        "top": "Hoje vamos automatizar uma pagina Dark no Instagram",
        "bottom": "Comenta \"eu quero\" que te mostro como funciona",
        "font_size": 74,
        "font_color": "white",
        "border_color": "black",
        "border_width": 6,
    },
    "captions": {"enabled": False, "burned_srt_path": ""},
    "frame": {
        "enabled": False,
        "background_color": "white",
        "header_background_color": "white",
        "divider_color": "#e02424",
        "divider_height": 8,
        "header_height": 340,
        "video_margin": 0,
        "video_fit": "crop",
        "logo_path": "",
        "logo_size": 164,
        "channel_name": "",
        "channel_color": "#111111",
        "channel_font_size": 72,
    },
    "broll": [],
    "watermark": {"enabled": True, "text": "@sistema.dark", "position": "bottom_right"},
    "audio": {
        "preserve": True,
        "normalize": True,
        "music_path": "",
        "music_volume": 0.22,
        "original_volume": 1.0,
    },
    "export": {"codec": "libx264", "crf": 23, "preset": "veryfast"},
}

RENDERED_RECIPE_KEYS = {"format", "trim", "text", "captions", "frame", "broll", "watermark", "audio", "export"}
CAPTION_RECIPE_KEYS = {"enabled", "burned_srt_path"}


PRESETS = [
    (
        "instagram_reels",
        "Instagram Reels",
        [
            "Conferir capa 9:16 antes de postar",
            "Colar legenda e hashtags do pacote",
            "Marcar como publicado no painel",
        ],
    ),
    (
        "tiktok",
        "TikTok",
        [
            "Revisar primeiro segundo do video",
            "Colar legenda sem links externos",
            "Validar audio depois do upload",
        ],
    ),
    (
        "youtube_shorts",
        "YouTube Shorts",
        [
            "Confirmar titulo curto e direto",
            "Usar thumbnail gerada como referencia",
            "Checar se o video ficou abaixo de 60s quando necessario",
        ],
    ),
]


PLATFORM_RULES = {
    "instagram_reels": {
        "rule_type": "organic_conservative",
        "source_url": None,
        "source_checked_at": "2026-06-19",
        "max_duration_seconds": None,
        "max_file_size_mb": None,
        "min_width": 720,
        "min_height": 720,
        "min_bitrate_kbps": None,
        "safe_zone": SAFE_ZONE_GUIDES["instagram_reels"],
        "notes": "Regra conservadora local ate validacao oficial Meta especifica para Reels organico.",
    },
    "tiktok": {
        "rule_type": "ads_specs",
        "source_url": "https://ads.tiktok.com/help/article/tiktok-auction-in-feed-ads",
        "source_checked_at": "2026-06-19",
        "max_duration_seconds": None,
        "max_file_size_mb": 500,
        "min_width": 540,
        "min_height": 960,
        "min_bitrate_kbps": 516,
        "safe_zone": SAFE_ZONE_GUIDES["tiktok"],
        "notes": "Fonte oficial de ads; diferenciar de regra organica em rodada futura se necessario.",
    },
    "youtube_shorts": {
        "rule_type": "organic",
        "source_url": "https://support.google.com/youtube/answer/15424877",
        "source_checked_at": "2026-06-19",
        "max_duration_seconds": 180,
        "max_file_size_mb": None,
        "min_width": None,
        "min_height": None,
        "min_bitrate_kbps": None,
        "safe_zone": SAFE_ZONE_GUIDES["youtube_shorts"],
        "notes": "Shorts quadrados ou verticais ate 3 minutos; atencao extra a Content ID acima de 1 minuto.",
    },
}


def _default_recipe_copy() -> dict:
    return json.loads(json.dumps(DEFAULT_RECIPE, ensure_ascii=False))


def normalize_renderable_recipe(recipe: dict | None) -> dict:
    """Keep persisted templates inside the recipe contract applied by render.py."""
    if not isinstance(recipe, dict):
        return _default_recipe_copy()

    defaults = _default_recipe_copy()
    normalized: dict = {}
    for key in RENDERED_RECIPE_KEYS:
        value = recipe.get(key, defaults.get(key))
        normalized[key] = value

    captions = normalized.get("captions")
    if not isinstance(captions, dict):
        captions = {}
    normalized["captions"] = {
        key: captions.get(key, defaults["captions"][key])
        for key in CAPTION_RECIPE_KEYS
    }

    broll = normalized.get("broll")
    if not isinstance(broll, list):
        normalized["broll"] = []

    frame = normalized.get("frame")
    if not isinstance(frame, dict):
        frame = {}
    normalized["frame"] = {**defaults["frame"], **frame}

    audio = normalized.get("audio")
    if not isinstance(audio, dict):
        audio = {}
    normalized["audio"] = {**defaults["audio"], **audio}

    for key, value in defaults.items():
        normalized.setdefault(key, value)
    return normalized


def _load_recipe(recipe_json: str) -> dict | None:
    try:
        loaded = json.loads(recipe_json)
    except (TypeError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def reconcile_template_recipes(db: Session) -> None:
    for template in db.query(Template).all():
        recipe = _load_recipe(template.recipe_json)
        normalized = normalize_renderable_recipe(recipe)
        if template.name == "Dark Instagram - CTA forte":
            template.description = "Template vertical inspirado nos videos de referencia."
        if normalized != recipe:
            template.recipe_json = json.dumps(normalized, ensure_ascii=False)


def apply_platform_rule_metadata(preset: PlatformPreset) -> None:
    rule = PLATFORM_RULES[preset.platform]
    preset.rule_type = rule["rule_type"]
    preset.source_url = rule["source_url"]
    preset.source_checked_at = rule["source_checked_at"]
    preset.max_duration_seconds = rule["max_duration_seconds"]
    preset.max_file_size_mb = rule["max_file_size_mb"]
    preset.min_width = rule["min_width"]
    preset.min_height = rule["min_height"]
    preset.min_bitrate_kbps = rule["min_bitrate_kbps"]
    preset.safe_zone_json = json.dumps(rule["safe_zone"], ensure_ascii=False)
    preset.notes = rule["notes"]


def seed_defaults(db: Session) -> None:
    if not db.query(Template).first():
        db.add(
            Template(
                name="Dark Instagram - CTA forte",
                description="Template vertical inspirado nos videos de referencia.",
                recipe_json=json.dumps(normalize_renderable_recipe(DEFAULT_RECIPE), ensure_ascii=False),
            )
        )

    for preset in template_presets():
        preset_prefix = preset["name"].split(" - ", 1)[0]
        existing = db.query(Template).filter(Template.name.like(f"{preset_prefix} - %")).first()
        if existing:
            existing.name = preset["name"]
            existing.description = preset["description"]
            existing.recipe_json = json.dumps(normalize_renderable_recipe(preset["recipe"]), ensure_ascii=False)
            continue
        db.add(
            Template(
                name=preset["name"],
                description=preset["description"],
                recipe_json=json.dumps(normalize_renderable_recipe(preset["recipe"]), ensure_ascii=False),
            )
        )

    reconcile_template_recipes(db)

    for platform, label, checklist in PRESETS:
        exists = db.query(PlatformPreset).filter(PlatformPreset.platform == platform).first()
        if exists:
            exists.label = label
            exists.width = 1080
            exists.height = 1920
            exists.codec = "H.264/AAC"
            exists.checklist_json = json.dumps(checklist, ensure_ascii=False)
            apply_platform_rule_metadata(exists)
            continue
        preset = PlatformPreset(
            platform=platform,
            label=label,
            width=1080,
            height=1920,
            codec="H.264/AAC",
            checklist_json=json.dumps(checklist, ensure_ascii=False),
        )
        apply_platform_rule_metadata(preset)
        db.add(preset)

    if not db.query(BrandKit).first():
        db.add(
            BrandKit(
                name="Dicas Tech",
                config_json=json.dumps(DEFAULT_BRAND_KIT, ensure_ascii=False),
                is_default=1,
            )
        )

    db.commit()
