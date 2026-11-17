from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import MarkerCreateRequest, SceneDetectRequest
from ..serializers import marker_to_dict, proxy_to_dict
from ..services.editor_tools import (
    create_marker,
    delete_marker,
    detect_and_store_scenes,
    export_presets,
    generate_asset_proxy,
    list_asset_proxies,
    list_markers,
)

router = APIRouter(prefix="/api/editor", tags=["editor-tools"])


@router.get("/export-presets")
def list_export_presets():
    return export_presets()


@router.get("/assets/{asset_id}/proxies")
def get_asset_proxies(asset_id: str, db: Session = Depends(get_db)):
    return [proxy_to_dict(proxy) for proxy in list_asset_proxies(db, asset_id)]


@router.post("/assets/{asset_id}/proxy")
def create_asset_proxy(asset_id: str, db: Session = Depends(get_db)):
    return proxy_to_dict(generate_asset_proxy(db, asset_id))


@router.get("/assets/{asset_id}/markers")
def get_asset_markers(asset_id: str, db: Session = Depends(get_db)):
    return [marker_to_dict(marker) for marker in list_markers(db, asset_id)]


@router.post("/assets/{asset_id}/markers")
def create_asset_marker(asset_id: str, payload: MarkerCreateRequest, db: Session = Depends(get_db)):
    marker = create_marker(
        db,
        asset_id,
        time_seconds=payload.time_seconds,
        duration_seconds=payload.duration_seconds,
        label=payload.label,
        color=payload.color,
        marker_type=payload.marker_type,
        notes=payload.notes,
    )
    return marker_to_dict(marker)


@router.post("/assets/{asset_id}/scene-detect")
def detect_asset_scenes(asset_id: str, payload: SceneDetectRequest, db: Session = Depends(get_db)):
    markers = detect_and_store_scenes(db, asset_id, threshold=payload.threshold, limit=payload.limit)
    return {"markers": [marker_to_dict(marker) for marker in markers], "count": len(markers)}


@router.post("/assets/{asset_id}/detect-silence")
def detect_asset_silence_route(
    asset_id: str,
    noise_db: float = -30.0,
    min_duration: float = 0.4,
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException
    from ..models import Asset
    from ..services.media import existing_asset_path
    from ..services.silence import analyze_asset_silence

    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset nao encontrado.")

    resolved_path = existing_asset_path(asset)
    if not resolved_path or not resolved_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de midia do asset nao encontrado no disco.")

    return analyze_asset_silence(resolved_path, noise_db=noise_db, min_duration=min_duration)


@router.delete("/markers/{marker_id}", status_code=204)
def remove_marker(marker_id: str, db: Session = Depends(get_db)):
    delete_marker(db, marker_id)
    return Response(status_code=204)

