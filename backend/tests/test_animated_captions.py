from __future__ import annotations

from app.services.captions import (
    VIRAL_PRESETS,
    SAFE_ZONE_PRESETS,
    EMOJI_KEYWORDS,
    chunk_words,
    build_ass_dynamic,
    clean_transcript_segments,
)


def test_viral_presets_and_safe_zones():
    assert 'hormozi' in VIRAL_PRESETS
    assert 'mrbeast' in VIRAL_PRESETS
    assert 'minimalist_clean' in VIRAL_PRESETS
    assert 'cyberpunk_neon' in VIRAL_PRESETS

    assert VIRAL_PRESETS['hormozi']['uppercase'] is True
    assert VIRAL_PRESETS['mrbeast']['animation'] == 'tilt_bounce'
    assert VIRAL_PRESETS['cyberpunk_neon']['animation'] == 'glow_pulse'

    assert 'tiktok' in SAFE_ZONE_PRESETS
    assert 'reels' in SAFE_ZONE_PRESETS
    assert 'shorts' in SAFE_ZONE_PRESETS
    assert SAFE_ZONE_PRESETS['tiktok']['margin_v'] >= 460


def test_chunk_words_rhythmic():
    words = [
        {'word': 'Como', 'start': 0.0, 'end': 0.3},
        {'word': 'criar', 'start': 0.3, 'end': 0.6},
        {'word': 'videos', 'start': 0.6, 'end': 0.9},
        {'word': 'virais', 'start': 0.9, 'end': 1.2},
        {'word': 'rapido', 'start': 2.0, 'end': 2.4},
    ]
    chunks = chunk_words(words, max_words=3, silence_gap=0.5)
    assert len(chunks) == 3
    assert len(chunks[0]) == 3
    assert len(chunks[1]) == 1
    assert len(chunks[2]) == 1



def test_build_ass_dynamic_with_emojis():
    segments = [{'start': 0.0, 'end': 1.5, 'text': 'ganhe muito dinheiro hoje'}]
    words = [
        {'word': 'ganhe', 'start': 0.0, 'end': 0.4},
        {'word': 'muito', 'start': 0.4, 'end': 0.8},
        {'word': 'dinheiro', 'start': 0.8, 'end': 1.4},
    ]
    ass = build_ass_dynamic(segments, words, preset='hormozi', enable_emojis=True)
    assert 'PlayResX: 1080' in ass
    assert 'PlayResY: 1920' in ass
    assert 'Montserrat' in ass
    assert 'Segoe UI Emoji' in ass
    assert '💰' in ass
    assert 'Dialogue:' in ass


def test_clean_transcript_segments():
    segments = [
        {'start': 0.0, 'end': 2.0, 'text': 'tipo assim eu basicamente criei o codigo'},
    ]
    cleaned = clean_transcript_segments(segments)
    assert 'tipo' not in cleaned[0]['text'].split()
    assert 'basicamente' not in cleaned[0]['text'].split()
    assert 'criei o codigo' in cleaned[0]['text']
