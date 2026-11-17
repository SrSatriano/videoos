from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..config import ALLOWED_RECIPE_MEDIA_ROOTS, path_is_within_roots
from ..schemas import MusicBriefRequest
from ..services.audio_lab import demucs_status, music_brief_from_prompt, separate_audio_stems
from ..services.media import path_is_allowed, resolve_user_path

router = APIRouter(prefix="/api/music", tags=["music"])


@router.get("/status")
def status():
    return demucs_status()


@router.post("/brief")
def brief(payload: MusicBriefRequest):
    return music_brief_from_prompt(payload.prompt)


@router.post("/separate-stems")
def separate_stems(payload: dict):
    raw_path = payload.get("audio_path") or payload.get("path")
    if not raw_path:
        raise HTTPException(status_code=400, detail="Parametro 'audio_path' e obrigatorio.")
    resolved = resolve_user_path(str(raw_path))
    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"Arquivo nao encontrado: {raw_path}")
    if not (path_is_allowed(resolved) or path_is_within_roots(resolved, ALLOWED_RECIPE_MEDIA_ROOTS)):
        raise HTTPException(status_code=403, detail="Acesso ao arquivo fora das raizes permitidas foi negado.")
    return separate_audio_stems(resolved)

