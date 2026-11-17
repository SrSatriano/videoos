from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.captions import (
    build_ass_karaoke,
    convert_srt_to_styled_ass,
    parse_subtitles_text,
)
from app.services.render import escape_drawtext, ffmpeg_color

client = TestClient(app)


def test_escape_drawtext_and_ffmpeg_color():
    # Test escaping of %, quotes, colons, newlines
    escaped = escape_drawtext("50% OFF: Promoção 'Especial'\nSegunda linha")
    assert "\\%" in escaped
    assert "\\:" in escaped
    assert "\\'" in escaped
    assert "\\n" in escaped

    # Test ffmpeg color parsing
    assert ffmpeg_color("#ffffff") == "0xffffff"
    assert ffmpeg_color("#ff000080") == "0xff000080"
    assert ffmpeg_color("rgba(255, 0, 0, 0.5)") == "0xff000080"
    assert ffmpeg_color("rgb(0, 255, 0)") == "0x00ff00"
    assert ffmpeg_color("yellow") == "yellow"


def test_subtitle_parser_and_karaoke_converter():
    srt_content = """1
00:00:01,000 --> 00:00:03,000
Primeiro teste de legenda

2
00:00:03,500 --> 00:00:06,000
<b>Segunda fala</b> com estilo
"""
    segments = parse_subtitles_text(srt_content)
    assert len(segments) == 2
    assert segments[0]["start"] == 1.0
    assert segments[0]["end"] == 3.0
    assert segments[0]["text"] == "Primeiro teste de legenda"
    assert segments[1]["text"] == "Segunda fala com estilo"  # HTML stripped

    # Test karaoke conversion with word interpolation when words are not provided
    karaoke_ass = build_ass_karaoke(segments)
    assert "\\k" in karaoke_ass
    assert "Primeiro" in karaoke_ass


def test_template_full_crud_and_duplicate():
    # 1. Create a template
    recipe = {
        "format": {"width": 1080, "height": 1920, "fit": "crop", "fps": 30},
        "trim": {"start": 0, "end": None},
        "text": {"top": "Hook Inicial", "bottom": "CTA Final", "font_size": 72, "font_color": "white", "border_color": "black", "border_width": 4},
        "captions": {"enabled": True, "style": "hormozi"},
        "frame": {"enabled": True, "background_color": "#ffffff", "header_background_color": "#ffffff", "divider_color": "#ff0000", "divider_height": 8, "header_height": 300, "video_margin": 0, "video_fit": "crop", "logo_path": "", "logo_size": 120, "channel_name": "Canal Teste", "channel_color": "#000000", "channel_font_size": 64},
        "broll": [],
        "watermark": {"enabled": True, "text": "@canal.teste", "position": "bottom_right"},
        "audio": {"preserve": True, "normalize": True, "music_volume": 0.2, "original_volume": 1.0},
        "export": {"codec": "libx264", "crf": 23, "preset": "veryfast"},
    }
    create_resp = client.post("/api/templates", json={"name": "Template Teste CRUD", "description": "Original", "recipe": recipe})
    assert create_resp.status_code == 200
    tpl_data = create_resp.json()
    tpl_id = tpl_data["id"]

    # 2. Get by ID
    get_resp = client.get(f"/api/templates/{tpl_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Template Teste CRUD"

    # 3. Update template (PUT)
    update_resp = client.put(f"/api/templates/{tpl_id}", json={"name": "Template Teste Atualizado", "description": "Atualizado"})
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Template Teste Atualizado"

    # 4. Duplicate template
    dup_resp = client.post(f"/api/templates/{tpl_id}/duplicate", json={"name": "Template Duplicado"})
    assert dup_resp.status_code == 200
    dup_data = dup_resp.json()
    assert dup_data["id"] != tpl_id
    assert dup_data["name"] == "Template Duplicado"

    # 5. Delete both templates
    del_resp1 = client.delete(f"/api/templates/{tpl_id}")
    assert del_resp1.status_code == 200
    del_resp2 = client.delete(f"/api/templates/{dup_data['id']}")
    assert del_resp2.status_code == 200

    # 6. Verify 404 on deleted
    assert client.get(f"/api/templates/{tpl_id}").status_code == 404
