from __future__ import annotations

from copy import deepcopy
from typing import Any


HOOKS = [
    "Voce esta perdendo tempo com isso",
    "Automatize esse processo hoje",
    "O jeito simples de criar conteudo",
    "Pare de editar tudo manualmente",
    "Essa rotina economiza horas",
    "Como crescer com videos curtos",
    "O truque que poucos usam",
    "Transforme uma ideia em 10 posts",
    "Seu conteudo precisa desse ajuste",
    "Antes de postar, faca isso",
]

CTA = [
    "Comenta 'eu quero' para receber",
    "Salva para testar depois",
    "Me chama para ver o passo a passo",
    "Envia para quem cria conteudo",
    "Comenta 'template' que eu te mando",
]

FILTER_FAMILIES = [
    ("contrast", "eq=contrast={value}:brightness=0.01:saturation=1.08"),
    ("warm", "colorbalance=rs={value}:gs=0.02:bs=-0.02"),
    ("cold", "colorbalance=rs=-0.02:gs=0.01:bs={value}"),
    ("sharp", "unsharp=5:5:{value}:5:5:0.0"),
    ("vignette", "vignette=PI/{value}"),
    ("grain", "noise=alls={value}:allf=t"),
    ("fade", "fade=t=in:st=0:d={value}"),
    ("saturate", "eq=saturation={value}"),
    ("cinema", "curves=preset=medium_contrast"),
    ("soft", "gblur=sigma={value}"),
]

MASK_SHAPES = [
    "circle",
    "rounded-rect",
    "vertical-band",
    "horizontal-band",
    "spotlight",
    "split-left",
    "split-right",
    "top-safe",
    "bottom-safe",
    "center-focus",
]

CAPTION_MODES = ["bold", "karaoke", "minimal", "boxed", "subtitle", "impact", "clean", "creator", "neon", "editorial"]


def base_recipe() -> dict[str, Any]:
    return {
        "format": {"width": 1080, "height": 1920, "fit": "crop", "fps": 30},
        "trim": {"start": 0, "end": None},
        "text": {
            "top": HOOKS[0],
            "bottom": CTA[0],
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


def template_presets() -> list[dict[str, Any]]:
    templates = []
    fit_modes = [("crop", "Fill"), ("contain", "Fit")]
    for index in range(50):
        recipe = deepcopy(base_recipe())
        fit, fit_label = fit_modes[index % len(fit_modes)]
        recipe["format"]["fit"] = fit
        recipe["text"]["top"] = HOOKS[index % len(HOOKS)]
        recipe["text"]["bottom"] = CTA[index % len(CTA)]
        recipe["text"]["font_size"] = 62 + (index % 7) * 4
        recipe["text"]["border_width"] = 4 + (index % 4)
        recipe["export"]["crf"] = 20 + (index % 7)
        recipe["captions"] = {"enabled": False, "burned_srt_path": ""}
        templates.append(
            {
                "id": f"template-{index + 1:02d}",
                "name": f"Template Massa {index + 1:02d} - {fit_label}",
                "description": "Preset vertical aplicado pelo renderizador atual com texto, watermark, audio e export.",
                "recipe": recipe,
            }
        )
    return templates


def filter_presets() -> list[dict[str, Any]]:
    filters = []
    for index in range(100):
        family, ffmpeg = FILTER_FAMILIES[index % len(FILTER_FAMILIES)]
        value = round(1.05 + (index % 10) * 0.08, 2)
        if family in {"sharp", "soft", "fade"}:
            value = round(0.25 + (index % 10) * 0.12, 2)
        if family == "grain":
            value = 3 + (index % 10)
        if family == "vignette":
            value = 3 + (index % 6)
        filters.append(
            {
                "id": f"filter-{index + 1:03d}",
                "name": f"Filtro {family.title()} {index + 1:03d}",
                "category": family,
                "ffmpeg": ffmpeg.format(value=value),
            }
        )
    return filters


def mask_presets() -> list[dict[str, Any]]:
    return [
        {
            "id": f"mask-{index + 1:03d}",
            "name": f"Mascara {MASK_SHAPES[index % len(MASK_SHAPES)].title()} {index + 1:03d}",
            "shape": MASK_SHAPES[index % len(MASK_SHAPES)],
            "opacity": round(0.22 + (index % 8) * 0.08, 2),
            "feather": 8 + (index % 10) * 4,
        }
        for index in range(100)
    ]


def caption_presets() -> list[dict[str, Any]]:
    return [
        {
            "id": f"caption-{index + 1:02d}",
            "name": f"Legenda {CAPTION_MODES[index % len(CAPTION_MODES)].title()} {index + 1:02d}",
            "mode": CAPTION_MODES[index % len(CAPTION_MODES)],
            "font_size": 54 + (index % 9) * 4,
            "font_color": "#ffffff" if index % 4 else "#ffd166",
            "outline": "#050607",
            "box": index % 5 == 0,
            "keyword_color": ["#51d88a", "#4da3ff", "#ffd166", "#ff7668"][index % 4],
        }
        for index in range(50)
    ]


def preset_library() -> dict[str, Any]:
    templates = template_presets()
    filters = filter_presets()
    masks = mask_presets()
    captions = caption_presets()
    return {
        "counts": {
            "templates": len(templates),
            "filters": len(filters),
            "masks": len(masks),
            "captions": len(captions),
        },
        "templates": templates,
        "filters": filters,
        "masks": masks,
        "captions": captions,
    }
