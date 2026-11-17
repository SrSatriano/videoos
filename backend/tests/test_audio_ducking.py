from __future__ import annotations

from app.services.audio_lab import (
    AUDIO_MOODS,
    classify_mood_from_prompt,
    build_vocal_clarity_filter,
    build_dynamic_ducking_filter,
)
from app.services.render import build_music_audio_filter_complex


def test_audio_moods_and_classification():
    assert len(AUDIO_MOODS) >= 5
    assert 'energetic' in AUDIO_MOODS
    assert 'inspiring' in AUDIO_MOODS
    assert 'mysterious' in AUDIO_MOODS
    assert 'lofi' in AUDIO_MOODS
    assert 'corporate' in AUDIO_MOODS

    assert classify_mood_from_prompt('quero um som com misterio e segredo') == 'mysterious'
    assert classify_mood_from_prompt('trilha animada com energia e hype') == 'energetic'
    assert classify_mood_from_prompt('fundo suave de programacao e codigo') == 'lofi'


def test_build_vocal_clarity_filter():
    f = build_vocal_clarity_filter({'highpass_hz': 80, 'presence_boost_db': 3.2})
    assert 'highpass=f=80' in f
    assert 'equalizer=f=3200' in f
    assert 'acompressor' in f


def test_build_dynamic_ducking_filter():
    duck = build_dynamic_ducking_filter(video_has_voice=True, strength=0.7)
    assert 'sidechaincompress' in duck
    assert 'threshold=' in duck
    assert 'attack=30' in duck


def test_render_music_audio_filter_with_ducking():
    recipe = {
        'audio': {
            'preserve': True,
            'music_volume': 0.2,
            'original_volume': 1.0,
            'fade_in': 1.0,
            'ducking': {'enabled': True, 'strength': 0.65},
            'voice_clarity': {'enabled': True},
        }
    }
    filter_complex = build_music_audio_filter_complex(recipe, music_input_index=1, input_has_audio=True)
    assert 'sidechaincompress' in filter_complex
    assert 'equalizer' in filter_complex
    assert 'amix=inputs=2' in filter_complex
