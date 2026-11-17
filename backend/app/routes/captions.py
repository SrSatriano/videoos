from __future__ import annotations

from fastapi import APIRouter

from ..schemas import CaptionExportRequest
from ..services.captions import build_srt, build_vtt, detect_filler_words

router = APIRouter(prefix="/api/captions", tags=["captions"])


@router.post("/export")
def export_captions(payload: CaptionExportRequest):
    text = build_vtt(payload.segments) if payload.format == "vtt" else build_srt(payload.segments)
    return {"format": payload.format, "text": text}


@router.post("/fillers")
def fillers(payload: CaptionExportRequest):
    text = " ".join(str(segment.get("text", "")) for segment in payload.segments)
    return {"words": detect_filler_words(text)}
