from __future__ import annotations

from fastapi import APIRouter

from ..schemas import BrollSuggestRequest
from ..services.broll import auto_match_broll_overlays, suggest_broll_cues

router = APIRouter(prefix="/api/broll", tags=["broll"])


@router.post("/suggest")
def suggest(payload: BrollSuggestRequest):
    return {"cues": suggest_broll_cues(payload.segments, payload.local_asset_keywords)}


@router.post("/auto-match")
def auto_match(payload: dict):
    segments = payload.get("segments", [])
    brolls = payload.get("available_brolls", [])
    max_overlays = int(payload.get("max_overlays", 4))
    matched = auto_match_broll_overlays(segments, brolls, max_overlays=max_overlays)
    return {"overlays": matched, "count": len(matched)}

