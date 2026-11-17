import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from ..config import TRANSCRIPTS_DIR, WHISPER_MODEL
from ..models import Asset
from .captions import build_srt, build_vtt


def transcription_status() -> dict[str, Any]:
    has_whisper_cli = bool(shutil.which("whisper"))
    has_faster_whisper = False
    try:
        import faster_whisper  # noqa
        has_faster_whisper = True
    except ImportError:
        has_faster_whisper = False

    engine = "faster-whisper" if has_faster_whisper else ("openai-whisper-cli" if has_whisper_cli else "none")
    return {
        "available": has_whisper_cli or has_faster_whisper,
        "engine": engine,
        "model": WHISPER_MODEL,
        "has_faster_whisper": has_faster_whisper,
        "has_whisper_cli": has_whisper_cli,
    }


def transcribe_asset(asset: Asset, *, language: str = "pt") -> dict[str, Any]:
    media_path = Path(asset.stored_path)
    if not media_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo do asset nao encontrado no disco.")

    output_dir = TRANSCRIPTS_DIR / asset.id
    output_dir.mkdir(parents=True, exist_ok=True)
    json_file = output_dir / "transcript.json"
    txt_file = output_dir / "transcript.txt"
    srt_file = output_dir / "transcript.srt"
    vtt_file = output_dir / "transcript.vtt"

    # Cache instantâneo: se já transcrito, reutilizar em 5ms evitando reprocessar a IA
    if json_file.exists() and txt_file.exists():
        try:
            cached_data = json.loads(json_file.read_text(encoding="utf-8"))
            if cached_data.get("text"):
                return {
                    "asset_id": asset.id,
                    "engine": "cache",
                    "path": str(txt_file),
                    "text": cached_data["text"],
                    "segments": cached_data.get("segments", []),
                    "words": cached_data.get("words", []),
                    "srt_path": str(srt_file),
                    "vtt_path": str(vtt_file),
                }
        except Exception:
            pass

    # 1. Try faster-whisper in-process if installed
    try:
        from faster_whisper import WhisperModel  # type: ignore


        model = WhisperModel(WHISPER_MODEL, device="auto", compute_type="default")
        segments_gen, info = model.transcribe(str(media_path), language=language, word_timestamps=True, vad_filter=True)
        segments: list[dict[str, Any]] = []
        words: list[dict[str, Any]] = []
        text_parts: list[str] = []

        for seg in segments_gen:
            seg_text = seg.text.strip()
            text_parts.append(seg_text)
            segments.append({
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": seg_text,
            })
            if hasattr(seg, "words") and seg.words:
                for w in seg.words:
                    words.append({
                        "word": w.word.strip(),
                        "start": round(w.start, 2),
                        "end": round(w.end, 2),
                        "probability": round(getattr(w, "probability", 1.0), 3),
                    })

        full_text = " ".join(text_parts)
        srt_content = build_srt(segments)
        vtt_content = build_vtt(segments)

        txt_file = output_dir / "transcript.txt"
        srt_file = output_dir / "transcript.srt"
        vtt_file = output_dir / "transcript.vtt"
        json_file = output_dir / "transcript.json"

        txt_file.write_text(full_text, encoding="utf-8")
        srt_file.write_text(srt_content, encoding="utf-8")
        vtt_file.write_text(vtt_content, encoding="utf-8")
        json_file.write_text(json.dumps({"text": full_text, "segments": segments, "words": words}, ensure_ascii=False), encoding="utf-8")

        return {
            "asset_id": asset.id,
            "engine": "faster-whisper",
            "path": str(txt_file),
            "text": full_text,
            "segments": segments,
            "words": words,
            "srt_path": str(srt_file),
            "vtt_path": str(vtt_file),
        }
    except ImportError:
        pass

    # 2. Fallback to whisper CLI
    whisper = shutil.which("whisper")
    if not whisper:
        raise HTTPException(
            status_code=501,
            detail="Nem faster-whisper nem Whisper CLI foram encontrados no ambiente. Instale openai-whisper ou faster-whisper.",
        )

    command = [
        whisper,
        str(media_path),
        "--model",
        WHISPER_MODEL,
        "--language",
        language,
        "--output_dir",
        str(output_dir),
        "--output_format",
        "all",
        "--word_timestamps",
        "True",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=1800)
    if completed.returncode != 0:
        raise HTTPException(status_code=500, detail=completed.stderr[-1200:] or "Whisper falhou.")

    txt_files = sorted(output_dir.glob("*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)
    json_files = sorted(output_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    srt_files = sorted(output_dir.glob("*.srt"), key=lambda path: path.stat().st_mtime, reverse=True)
    vtt_files = sorted(output_dir.glob("*.vtt"), key=lambda path: path.stat().st_mtime, reverse=True)

    transcript_text = txt_files[0].read_text(encoding="utf-8") if txt_files else ""
    segments: list[dict[str, Any]] = []
    words: list[dict[str, Any]] = []

    if json_files:
        try:
            data = json.loads(json_files[0].read_text(encoding="utf-8"))
            raw_segments = data.get("segments", [])
            for seg in raw_segments:
                segments.append({
                    "start": round(float(seg.get("start", 0)), 2),
                    "end": round(float(seg.get("end", 0)), 2),
                    "text": seg.get("text", "").strip(),
                })
                for w in seg.get("words", []):
                    words.append({
                        "word": w.get("word", "").strip(),
                        "start": round(float(w.get("start", 0)), 2),
                        "end": round(float(w.get("end", 0)), 2),
                        "probability": round(float(w.get("probability", 1.0)), 3),
                    })
        except Exception:
            pass

    if not segments:
        duration = float(asset.duration_seconds or 1.0)
        segments = [{"start": 0.0, "end": max(duration, 1.0), "text": transcript_text}]

    return {
        "asset_id": asset.id,
        "engine": "openai-whisper-cli",
        "path": str(txt_files[0]) if txt_files else str(output_dir),
        "text": transcript_text,
        "segments": segments,
        "words": words,
        "srt_path": str(srt_files[0]) if srt_files else None,
        "vtt_path": str(vtt_files[0]) if vtt_files else None,
    }

