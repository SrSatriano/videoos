from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Batch
from ..schemas import BatchCreate, RetryRequest
from ..serializers import batch_to_dict
from ..services.queue import cancel_batch, create_batch, pause_batch, resume_batch, retry_batch

router = APIRouter(prefix="/api/batches", tags=["batches"])


@router.get("")
def list_batches(db: Session = Depends(get_db)):
    batches = (
        db.query(Batch)
        .options(joinedload(Batch.jobs))
        .order_by(Batch.created_at.desc())
        .all()
    )
    return [batch_to_dict(batch) for batch in batches]


@router.post("")
def create_render_batch(payload: BatchCreate, db: Session = Depends(get_db)):
    try:
        batch = create_batch(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.refresh(batch)
    return batch_to_dict(batch)


@router.post("/{batch_id}/pause")
def pause_render_batch(batch_id: str, db: Session = Depends(get_db)):
    batch = db.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Lote nao encontrado.")
    try:
        updated = pause_batch(db, batch)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return batch_to_dict(updated)


@router.post("/{batch_id}/resume")
def resume_render_batch(batch_id: str, db: Session = Depends(get_db)):
    batch = db.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Lote nao encontrado.")
    try:
        updated = resume_batch(db, batch)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return batch_to_dict(updated)


@router.post("/{batch_id}/cancel")
def cancel_render_batch(batch_id: str, db: Session = Depends(get_db)):
    batch = db.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Lote nao encontrado.")
    try:
        updated = cancel_batch(db, batch)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return batch_to_dict(updated)


@router.post("/{batch_id}/retry")
def retry_render_batch(batch_id: str, payload: RetryRequest, db: Session = Depends(get_db)):
    batch = db.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Lote nao encontrado.")
    try:
        updated = retry_batch(db, batch, reset_attempts=payload.reset_attempts)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return batch_to_dict(updated)
