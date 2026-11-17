from __future__ import annotations


def suggest_broll_cues(segments: list[dict], local_asset_keywords: list[str]) -> list[dict]:
    cues = []
    for segment in segments:
        text = str(segment.get("text", "")).lower()
        for keyword in local_asset_keywords:
            if keyword.lower() in text:
                cues.append(
                    {
                        "start_seconds": float(segment.get("start", 0)),
                        "end_seconds": float(segment.get("end", 0)),
                        "keyword": keyword,
                        "prompt": f"Mostrar apoio visual de {keyword}",
                        "source": "local",
                    }
                )
                break
    return cues


def auto_match_broll_overlays(
    segments: list[dict],
    available_brolls: list[dict],
    max_overlays: int = 4,
    min_gap_seconds: float = 0.5,
) -> list[dict]:
    """Matches B-Roll videos to spoken text segments based on keywords or filename matches."""
    matched = []
    last_end = 0.0

    for segment in segments:
        if len(matched) >= max_overlays:
            break
        seg_start = float(segment.get("start", 0.0))
        seg_end = float(segment.get("end", 0.0))
        if matched and seg_start < last_end + min_gap_seconds:
            continue

        seg_text = str(segment.get("text", "")).lower()
        for broll in available_brolls:
            broll_tags = [str(t).lower() for t in broll.get("tags", [])]
            broll_name = str(broll.get("name", "")).lower()

            matches = any(t in seg_text for t in broll_tags if len(t) > 2) or (
                len(broll_name) > 3 and broll_name.replace(".mp4", "") in seg_text
            )

            if matches:
                broll_dur = float(broll.get("duration_seconds", 3.0) or 3.0)
                dur = min(max(seg_end - seg_start, 1.5), broll_dur, 4.0)
                matched.append(
                    {
                        "path": broll["path"],
                        "start": round(seg_start, 2),
                        "end": round(seg_start + dur, 2),
                        "opacity": 0.95,
                        "layout": "cover",
                        "keyword_matched": broll.get("name", "broll"),
                    }
                )
                last_end = seg_start + dur
                break

    return matched

