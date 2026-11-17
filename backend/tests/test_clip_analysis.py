from __future__ import annotations

from app.services.clip_analysis import score_segment, split_transcript_into_candidates


def test_score_segment_rewards_hooks_and_cta():
    hot = score_segment("Voce esta perdendo dinheiro porque ainda faz isso manualmente")
    cold = score_segment("hoje eu acordei e abri o computador")
    assert hot > cold


def test_split_transcript_into_candidates_limits_duration():
    segments = [
        {"start": 0, "end": 8, "text": "primeiro ponto importante"},
        {"start": 8, "end": 20, "text": "segundo ponto com automacao"},
        {"start": 20, "end": 42, "text": "comenta eu quero para receber"},
    ]
    candidates = split_transcript_into_candidates(segments, min_seconds=10, max_seconds=35)
    assert candidates
    assert all(10 <= item["end_seconds"] - item["start_seconds"] <= 35 for item in candidates)
