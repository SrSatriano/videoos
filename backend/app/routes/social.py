from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import DownloadJob
from ..schemas import InstagramCaptureRequest
from ..services.social import (
    enqueue_download_job,
    instagram_status,
    run_download_job_in_background,
    serialize_download_job,
    store_cookie_upload,
)

router = APIRouter(prefix="/api/social", tags=["social"])


@router.get("/instagram/status")
def status():
    return instagram_status()


@router.post("/cookies")
async def upload_cookies(file: UploadFile = File(...)):
    content = await file.read()
    return store_cookie_upload(file.filename or "cookies.txt", content)


@router.post("/instagram/capture")
def capture_instagram(
    payload: InstagramCaptureRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    job = enqueue_download_job(
        db,
        source=payload.source,
        limit=payload.limit,
        offset=payload.offset,
        rights_confirmed=payload.rights_confirmed,
        import_to_library=payload.import_to_library,
        cookies_from_browser=payload.cookies_from_browser,
        cookies_file_path=payload.cookies_file_path,
        destination=payload.destination,
    )
    background_tasks.add_task(run_download_job_in_background, job.id)
    return serialize_download_job(job)


@router.get("/downloads")
def list_downloads(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(DownloadJob).order_by(DownloadJob.created_at.desc())
    if status:
        query = query.filter(DownloadJob.status == status)
    return [serialize_download_job(job) for job in query.limit(limit).all()]


@router.get("/downloads/{job_id}")
def get_download(job_id: str, db: Session = Depends(get_db)):
    job = db.get(DownloadJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Download nao encontrado.")
    return serialize_download_job(job)
