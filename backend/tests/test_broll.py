from __future__ import annotations

from app.services.broll import suggest_broll_cues


def test_suggest_broll_cues_from_transcript():
    cues = suggest_broll_cues(
        [{"start": 0, "end": 5, "text": "abre o Instagram e automatiza as respostas"}],
        local_asset_keywords=["instagram", "automacao"],
    )
    assert cues[0]["keyword"] in {"instagram", "automacao"}
    assert cues[0]["start_seconds"] == 0
