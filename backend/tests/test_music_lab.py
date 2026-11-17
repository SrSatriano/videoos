from __future__ import annotations

from app.services.audio_lab import build_music_duck_filter, music_brief_from_prompt


def test_music_brief_from_prompt():
    brief = music_brief_from_prompt("trilha tech futurista para tutorial rapido")
    assert brief["mood"] == "tech"
    assert "tutorial" in brief["description"]


def test_build_music_duck_filter():
    filter_value = build_music_duck_filter(video_has_voice=True)
    assert "sidechaincompress" in filter_value
