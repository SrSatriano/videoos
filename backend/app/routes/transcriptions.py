from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Asset, Transcript
from ..schemas import ManualTranscriptionRequest, TranscriptionRequest, TranscriptUpdateRequest
from ..serializers import transcript_to_dict
from ..services.captions import build_ass_karaoke, build_srt, build_vtt
from ..services.transcription import transcribe_asset, transcription_status

router = APIRouter(prefix="/api/transcriptions", tags=["transcriptions"])


@router.get("/status")
def status():
    return transcription_status()


@router.get("")
def list_transcriptions(asset_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Transcript).order_by(Transcript.created_at.desc())
    if asset_id:
        query = query.filter(Transcript.asset_id == asset_id)
    return [transcript_to_dict(transcript) for transcript in query.limit(100).all()]


@router.get("/{transcript_id}")
def get_transcription(transcript_id: str, db: Session = Depends(get_db)):
    transcript = db.get(Transcript, transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcricao nao encontrada.")
    return transcript_to_dict(transcript)


@router.post("")
def create_transcription(payload: TranscriptionRequest, db: Session = Depends(get_db)):
    asset = db.get(Asset, payload.asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset nao encontrado.")
    result = transcribe_asset(asset, language=payload.language)
    duration = float(asset.duration_seconds or 0)
    segments = result.get("segments") or [{"start": 0, "end": max(duration, 1.0), "text": result.get("text", "")}]
    words = result.get("words") or []
    transcript = Transcript(
        asset_id=asset.id,
        engine=result.get("engine", "openai-whisper-cli"),
        language=payload.language,
        text=result.get("text", ""),
        segments_json=json.dumps(segments, ensure_ascii=False),
        words_json=json.dumps(words, ensure_ascii=False),
        status="completed",
    )
    db.add(transcript)
    db.commit()
    result["transcript_id"] = transcript.id
    return result


@router.post("/manual")
def create_manual_transcription(payload: ManualTranscriptionRequest, db: Session = Depends(get_db)):
    asset = db.get(Asset, payload.asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset nao encontrado.")
    duration = float(asset.duration_seconds or 1)
    transcript = Transcript(
        asset_id=asset.id,
        engine="manual",
        language=payload.language,
        text=payload.text,
        segments_json=json.dumps([{"start": 0, "end": max(duration, 1.0), "text": payload.text}], ensure_ascii=False),
        words_json="[]",
        status="completed",
    )
    db.add(transcript)
    db.commit()
    db.refresh(transcript)
    return transcript_to_dict(transcript)


@router.patch("/{transcript_id}")
def update_transcription(
    transcript_id: str,
    payload: TranscriptUpdateRequest,
    db: Session = Depends(get_db),
):
    transcript = db.get(Transcript, transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcricao nao encontrada.")

    if payload.text is not None:
        transcript.text = payload.text
    if payload.segments is not None:
        transcript.segments_json = json.dumps(payload.segments, ensure_ascii=False)
    if payload.words is not None:
        transcript.words_json = json.dumps(payload.words, ensure_ascii=False)

    db.commit()
    db.refresh(transcript)
    return transcript_to_dict(transcript)


@router.get("/{transcript_id}/subtitles")
def get_transcript_subtitles(
    transcript_id: str,
    format: Literal["srt", "vtt", "ass"] = Query("srt"),
    db: Session = Depends(get_db),
):
    transcript = db.get(Transcript, transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcricao nao encontrada.")

    try:
        segments = json.loads(transcript.segments_json)
    except Exception:
        segments = [{"start": 0.0, "end": 1.0, "text": transcript.text}]

    try:
        words = json.loads(transcript.words_json)
    except Exception:
        words = []

    if format == "ass":
        content = build_ass_karaoke(segments, words)
        media_type = "text/x-ssa"
    elif format == "vtt":
        content = build_vtt(segments)
        media_type = "text/vtt"
    else:
        content = build_srt(segments)
        media_type = "text/plain"

    return PlainTextResponse(content=content, media_type=media_type)


