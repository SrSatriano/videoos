from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import BatchQualityCheckRequest, QualityCheckRequest
from ..services.quality import (
    check_asset_integrity,
    check_render_integrity,
    quality_check_batch,
    quality_check_render,
)

router = APIRouter(prefix="/api/quality", tags=["quality"])


@router.post("/renders/{rendered_id}")
def check_render_quality(rendered_id: str, payload: QualityCheckRequest, db: Session = Depends(get_db)):
    return quality_check_render(db, rendered_id, payload.platforms)


@router.post("/batches/{batch_id}")
def check_batch_quality(
    batch_id: str,
    payload: BatchQualityCheckRequest | None = None,
    db: Session = Depends(get_db),
):
    platforms = payload.platforms if payload else None
    return quality_check_batch(db, batch_id, platforms)


@router.get("/batches/{batch_id}")
def get_batch_quality_summary(batch_id: str, db: Session = Depends(get_db)):
    return quality_check_batch(db, batch_id)


@router.post("/assets/{asset_id}/integrity")
def asset_integrity(asset_id: str, db: Session = Depends(get_db)):
    return check_asset_integrity(db, asset_id)


@router.post("/renders/{rendered_id}/integrity")
def render_integrity(rendered_id: str, db: Session = Depends(get_db)):
    return check_render_integrity(db, rendered_id)


