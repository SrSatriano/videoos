from __future__ import annotations

from app.services.silence import compute_speech_intervals, detect_silence_intervals
from app.services.captions import KARAOKE_THEMES, build_ass_karaoke


def test_karaoke_themes_and_build_ass_with_theme() -> None:
    assert "hormozi" in KARAOKE_THEMES
    assert "neon_cyan" in KARAOKE_THEMES
    assert "minimal_white" in KARAOKE_THEMES
    assert "bold_red" in KARAOKE_THEMES

    segments = [{"start": 0.0, "end": 2.0, "text": "Teste Hormozi"}]
    words = [
        {"word": "Teste", "start": 0.0, "end": 0.8, "probability": 0.99},
        {"word": "Hormozi", "start": 0.8, "end": 2.0, "probability": 0.98},
    ]

    ass_hormozi = build_ass_karaoke(segments, words, theme="hormozi")
    assert "Montserrat" in ass_hormozi
    assert "&H0000E6FF" in ass_hormozi
    assert "{\\k80}Teste {\\k120}Hormozi" in ass_hormozi

    ass_neon = build_ass_karaoke(segments, words, theme="neon_cyan")
    assert "&H00FFFF00" in ass_neon


def test_compute_speech_intervals_with_silence() -> None:
    total_duration = 10.0
    silences = [(2.0, 4.0), (7.0, 8.5)]

    result = compute_speech_intervals(total_duration, silences, pad=0.05)
    assert result["total_duration"] == 10.0
    assert result["silences_count"] == 2
    assert result["silence_duration"] > 0
    assert result["speech_duration"] < 10.0
    assert len(result["intervals"]) == 3
    assert result["intervals"][0]["start"] == 0.0


def test_compute_speech_intervals_no_silence() -> None:
    result = compute_speech_intervals(5.0, [])
    assert result["total_duration"] == 5.0
    assert result["silences_count"] == 0
    assert result["removed_seconds"] == 0.0
    assert len(result["intervals"]) == 1
