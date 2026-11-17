from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import RenderJob, RenderedVideo, now_utc
from ..schemas import RenderedVideoUpdate, RetryRequest
from ..serializers import job_to_dict, rendered_to_dict
from ..services.audit import record_event
from ..services.queue import cancel_job, claim_next_job, process_job, retry_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
renders_router = APIRouter(prefix="/api/renders", tags=["renders"])


@router.get("")
def list_jobs(
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = (
        db.query(RenderJob)
        .options(joinedload(RenderJob.asset), joinedload(RenderJob.template))
        .order_by(RenderJob.created_at.desc())
    )
    if status:
        query = query.filter(RenderJob.status == status)
    return [job_to_dict(job) for job in query.all()]


@router.post("/process-next")
def process_next_job(db: Session = Depends(get_db)):
    active_jobs = db.query(RenderJob).filter(RenderJob.status == "processing").count()
    if active_jobs > 0:
        return {"processed": None, "message": f"Ja existe um job em processamento ({active_jobs})."}
    job = claim_next_job(db)
    if not job:
        return {"processed": None, "message": "Nenhum job na fila."}
    processed = process_job(db, job)
    return {"processed": job_to_dict(processed)}


@router.post("/{job_id}/retry")
def retry_render_job(job_id: str, payload: RetryRequest, db: Session = Depends(get_db)):
    job = db.get(RenderJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nao encontrado.")
    try:
        updated = retry_job(db, job, reset_attempts=payload.reset_attempts)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return job_to_dict(updated)


@router.post("/{job_id}/cancel")
def cancel_render_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(RenderJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nao encontrado.")
    try:
        updated = cancel_job(db, job)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return job_to_dict(updated)


@renders_router.get("")
def list_renders(
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(RenderedVideo).order_by(RenderedVideo.created_at.desc())
    if status:
        query = query.filter(RenderedVideo.status == status)
    return [rendered_to_dict(rendered) for rendered in query.all()]


@renders_router.patch("/{rendered_id}")
def update_rendered_video(
    rendered_id: str,
    payload: RenderedVideoUpdate,
    db: Session = Depends(get_db),
):
    rendered = db.get(RenderedVideo, rendered_id)
    if not rendered:
        raise HTTPException(status_code=404, detail="Render nao encontrado.")
    rendered.status = payload.status
    rendered.reviewed_at = now_utc()
    db.commit()
    db.refresh(rendered)
    record_event(
        db,
        event_type="render_reviewed",
        entity_type="rendered_video",
        entity_id=rendered.id,
        message=f"Render marcado como {payload.status}.",
    )
    return rendered_to_dict(rendered)
