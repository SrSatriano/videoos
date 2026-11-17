from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .media import ensure_ffmpeg, ffprobe_metadata


def detect_silence_intervals(
    media_path: Path | str,
    noise_db: float = -30.0,
    min_duration: float = 0.4,
) -> list[tuple[float, float]]:
    ensure_ffmpeg()
    path = Path(media_path).resolve()
    if not path.exists():
        return []

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-af",
        f"silencedetect=noise={noise_db}dB:d={min_duration}",
        "-f",
        "null",
        "-",
    ]

    try:
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
            check=False,
        )
        stderr_text = process.stderr
    except Exception:
        return []

    silences: list[tuple[float, float]] = []
    current_start: float | None = None

    for line in stderr_text.splitlines():
        start_match = re.search(r"silence_start:\s*([0-9.]+)", line)
        if start_match:
            current_start = float(start_match.group(1))

        end_match = re.search(r"silence_end:\s*([0-9.]+)", line)
        if end_match:
            end_val = float(end_match.group(1))
            start_val = current_start if current_start is not None else 0.0
            if end_val > start_val:
                silences.append((start_val, end_val))
            current_start = None

    if current_start is not None:
        try:
            meta = ffprobe_metadata(path)
            dur = float(meta.get("duration_seconds", 0.0) or 0.0)
            if dur > current_start:
                silences.append((current_start, dur))
        except Exception:
            pass

    return silences


def compute_speech_intervals(
    total_duration: float,
    silences: list[tuple[float, float]],
    pad: float = 0.05,
) -> dict:
    if not silences:
        return {
            "total_duration": total_duration,
            "speech_duration": total_duration,
            "silence_duration": 0.0,
            "removed_seconds": 0.0,
            "intervals": [{"start": 0.0, "end": total_duration}],
            "silences_count": 0,
        }

    speech: list[dict[str, float]] = []
    cursor = 0.0

    for s_start, s_end in silences:
        seg_start = max(0.0, cursor)
        seg_end = min(total_duration, s_start + pad)
        if seg_end - seg_start > 0.15:
            speech.append({"start": round(seg_start, 3), "end": round(seg_end, 3)})
        cursor = max(cursor, s_end - pad)

    if cursor < total_duration:
        seg_start = max(0.0, cursor)
        seg_end = total_duration
        if seg_end - seg_start > 0.15:
            speech.append({"start": round(seg_start, 3), "end": round(seg_end, 3)})

    speech_dur = sum(item["end"] - item["start"] for item in speech)
    silence_dur = max(0.0, total_duration - speech_dur)

    return {
        "total_duration": round(total_duration, 3),
        "speech_duration": round(speech_dur, 3),
        "silence_duration": round(silence_dur, 3),
        "removed_seconds": round(silence_dur, 3),
        "intervals": speech if speech else [{"start": 0.0, "end": total_duration}],
        "silences_count": len(silences),
    }


def analyze_asset_silence(media_path: Path | str, noise_db: float = -30.0, min_duration: float = 0.4) -> dict:
    meta = ffprobe_metadata(Path(media_path))
    duration = float(meta.get("duration_seconds", 0.0) or 0.0)
    if duration <= 0.0:
        return {"error": "Duracao do video invalida ou arquivo inacessivel."}

    silences = detect_silence_intervals(media_path, noise_db=noise_db, min_duration=min_duration)
    return compute_speech_intervals(duration, silences)


def compute_smart_speech_intervals(
    total_duration: float,
    silences: list[tuple[float, float]],
    pre_pad: float = 0.05,
    post_pad: float = 0.10,
    fade_duration: float = 0.015,
) -> dict:
    """Calcula intervalos de fala com padding assimétrico e marcação de micro-fades para evitar estalos de áudio."""
    if not silences:
        return {
            "total_duration": round(total_duration, 3),
            "speech_duration": round(total_duration, 3),
            "silence_duration": 0.0,
            "removed_seconds": 0.0,
            "intervals": [{"start": 0.0, "end": round(total_duration, 3), "fade_in": fade_duration, "fade_out": fade_duration}],
            "silences_count": 0,
            "fade_duration": fade_duration,
        }

    speech: list[dict[str, float]] = []
    cursor = 0.0

    for s_start, s_end in silences:
        seg_start = max(0.0, cursor)
        seg_end = min(total_duration, s_start + post_pad)
        if seg_end - seg_start > 0.12:
            speech.append({
                "start": round(seg_start, 3),
                "end": round(seg_end, 3),
                "fade_in": fade_duration if seg_start > 0.0 else 0.0,
                "fade_out": fade_duration,
            })
        cursor = max(cursor, s_end - pre_pad)

    if cursor < total_duration:
        seg_start = max(0.0, cursor)
        seg_end = total_duration
        if seg_end - seg_start > 0.12:
            speech.append({
                "start": round(seg_start, 3),
                "end": round(seg_end, 3),
                "fade_in": fade_duration,
                "fade_out": 0.0,
            })

    speech_dur = sum(item["end"] - item["start"] for item in speech)
    silence_dur = max(0.0, total_duration - speech_dur)

    return {
        "total_duration": round(total_duration, 3),
        "speech_duration": round(speech_dur, 3),
        "silence_duration": round(silence_dur, 3),
        "removed_seconds": round(silence_dur, 3),
        "intervals": speech if speech else [{"start": 0.0, "end": round(total_duration, 3), "fade_in": 0.0, "fade_out": 0.0}],
        "silences_count": len(silences),
        "fade_duration": fade_duration,
    }


