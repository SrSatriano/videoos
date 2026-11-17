from __future__ import annotations

HOT_WORDS = ("perdendo", "segredo", "automatizar", "automacao", "gratis", "erro", "dinheiro", "instagram", "comenta")


def score_segment(text: str) -> float:
    lowered = text.lower()
    score = 0.2
    score += min(0.4, len(text) / 400)
    score += sum(0.08 for word in HOT_WORDS if word in lowered)
    if "?" in text:
        score += 0.1
    if "comenta" in lowered or "eu quero" in lowered:
        score += 0.15
    return round(min(score, 1.0), 3)


def _overlap_ratio(cand_a: dict, cand_b: dict) -> float:
    start = max(cand_a["start_seconds"], cand_b["start_seconds"])
    end = min(cand_a["end_seconds"], cand_b["end_seconds"])
    if end <= start:
        return 0.0
    intersection = end - start
    dur_a = cand_a["end_seconds"] - cand_a["start_seconds"]
    dur_b = cand_b["end_seconds"] - cand_b["start_seconds"]
    min_dur = min(dur_a, dur_b)
    return intersection / min_dur if min_dur > 0 else 0.0


def split_transcript_into_candidates(segments: list[dict], min_seconds: int, max_seconds: int) -> list[dict]:
    raw_candidates: list[dict] = []
    for start_index, segment in enumerate(segments):
        text_parts = []
        start = float(segment["start"])
        best_in_window: dict | None = None
        for next_segment in segments[start_index:]:
            end = float(next_segment["end"])
            text_parts.append(str(next_segment["text"]).strip())
            duration = end - start
            if duration >= min_seconds:
                if duration > max_seconds:
                    break
                text = " ".join(text_parts)
                cand = {
                    "start_seconds": start,
                    "end_seconds": round(end, 2),
                    "score": score_segment(text),
                    "hook": text[:140],
                    "reason": "Corte sugerido por densidade de fala, palavras de impacto e CTA.",
                }
                if best_in_window is None or cand["score"] > best_in_window["score"]:
                    best_in_window = cand
        if best_in_window is not None:
            raw_candidates.append(best_in_window)

    sorted_candidates = sorted(raw_candidates, key=lambda item: item["score"], reverse=True)

    selected: list[dict] = []
    for cand in sorted_candidates:
        if not any(_overlap_ratio(cand, kept) > 0.4 for kept in selected):
            selected.append(cand)
            if len(selected) >= 15:
                break
    return selected if selected else sorted_candidates[:10]
