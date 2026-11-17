from __future__ import annotations

from app.services.captions import build_srt, detect_filler_words


def test_build_srt_uses_timestamp_format():
    srt = build_srt([{"start": 1.2, "end": 3.4, "text": "fala importante"}])
    assert "00:00:01,200 --> 00:00:03,400" in srt
    assert "fala importante" in srt


def test_detect_filler_words_pt_br():
    result = detect_filler_words("tipo assim eu acho que voce sabe")
    assert "tipo" in result
    assert "assim" in result
