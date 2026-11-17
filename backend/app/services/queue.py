from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from ..config import RENDERS_DIR, THUMBNAILS_DIR
from ..database import SessionLocal
from ..models import Asset, Batch, RenderJob, RenderedVideo, Template, now_utc
from ..schemas import BatchCreate
from .audit import record_event
from .path_policy import resolve_allowed_directory
from .render import RenderCanceledError, copy_recipe_manifest, load_recipe, render_video
from .storage import check_storage_capacity


TERMINAL_STATUSES = {"completed", "failed", "canceled"}


def create_batch(db: Session, payload: BatchCreate) -> Batch:
    template = db.get(Template, payload.template_id)
    if not template:
        raise ValueError("Template nao encontrado.")
    assets = db.query(Asset).filter(Asset.id.in_(payload.asset_ids)).all()
    if len(assets) != len(set(payload.asset_ids)):
        raise ValueError("Um ou mais assets nao foram encontrados.")
    output_dir = None
    if payload.output_dir and payload.output_dir.strip():
        output_dir = str(resolve_allowed_directory(payload.output_dir, field_name="output_dir"))
    if payload.estimated_output_bytes is not None:
        storage = check_storage_capacity(output_dir, payload.estimated_output_bytes)
        if not storage["has_capacity"]:
            raise ValueError(
                "Espaco seguro insuficiente para o lote: "
                f"necessario {storage['required_bytes']} bytes; "
                f"disponivel {storage['safe_available_bytes']} bytes apos reserva."
            )

    batch = Batch(
        name=payload.name,
        template_id=payload.template_id,
        status="queued",
        total_jobs=len(assets) * payload.variations,
        output_dir=output_dir,
    )
    db.add(batch)
    db.flush()
    for variation in range(1, payload.variations + 1):
        for asset in assets:
            db.add(
                RenderJob(
                    batch_id=batch.id,
                    asset_id=asset.id,
                    template_id=template.id,
                    variation_index=variation,
                    status="queued",
                    progress=0,
                    current_step="Na fila",
                )
            )
    db.commit()
    db.refresh(batch)
    record_event(
        db,
        event_type="batch_created",
        entity_type="batch",
        entity_id=batch.id,
        message=f"Lote criado com {batch.total_jobs} job(s).",
        payload={"template_id": template.id, "asset_ids": payload.asset_ids, "output_dir": output_dir},
    )
    return batch


def next_queued_job(db: Session) -> RenderJob | None:
    return (
        db.query(RenderJob)
        .options(joinedload(RenderJob.asset), joinedload(RenderJob.template))
        .join(Batch, RenderJob.batch_id == Batch.id)
        .filter(
            RenderJob.status == "queued",
            RenderJob.cancel_requested.is_(False),
            Batch.is_paused.is_(False),
        )
        .order_by(RenderJob.created_at.asc())
        .first()
    )


def claim_next_job(db: Session) -> RenderJob | None:
    candidate = next_queued_job(db)
    if not candidate:
        return None

    claimed = db.execute(
        update(RenderJob)
        .where(
            RenderJob.id == candidate.id,
            RenderJob.status == "queued",
            RenderJob.cancel_requested.is_(False),
            RenderJob.batch_id.in_(select(Batch.id).where(Batch.is_paused.is_(False))),
        )
        .values(
            status="processing",
            progress=5,
            current_step="Reservado para render",
            attempts=RenderJob.attempts + 1,
            started_at=now_utc(),
            error_message=None,
            cancel_requested=False,
        )
    )
    db.commit()
    if claimed.rowcount != 1:
        return None

    job = (
        db.query(RenderJob)
        .options(joinedload(RenderJob.asset), joinedload(RenderJob.template))
        .filter(RenderJob.id == candidate.id)
        .one()
    )
    update_batch_status(db, job.batch_id)
    return job


def recover_interrupted_jobs(db: Session) -> int:
    jobs = db.query(RenderJob).filter(RenderJob.status == "processing").all()
    if not jobs:
        return 0

    batch_ids = {job.batch_id for job in jobs}
    canceled_ids: list[str] = []
    requeued_ids: list[str] = []
    failed_ids: list[str] = []
    from ..config import RENDERS_DIR
    for job in jobs:
        # Purgar arquivos parciais e temporarios do job interrompido
        for tmp_file in RENDERS_DIR.rglob(f"*{job.id}*tmp*"):
            try:
                tmp_file.unlink(missing_ok=True)
            except Exception:
                pass

        if job.cancel_requested:
            job.status = "canceled"
            job.progress = 100
            job.current_step = "Cancelado"
            job.error_message = None
            job.finished_at = now_utc()
            canceled_ids.append(job.id)
        elif job.attempts >= 3:
            job.status = "failed"
            job.progress = 100
            job.current_step = "Falhou por quedas sucessivas"
            job.error_message = f"Job abortado apos {job.attempts} tentativas interrompidas abruptamente (protecao poison pill)."
            job.finished_at = now_utc()
            failed_ids.append(job.id)
        else:
            job.status = "queued"
            job.progress = 0
            job.current_step = "Recuperado apos reinicio"
            job.error_message = "Job voltou para a fila porque o worker reiniciou durante o processamento."
            job.started_at = None
            job.finished_at = None
            requeued_ids.append(job.id)
        job.cancel_requested = False
    db.commit()


    for batch_id in batch_ids:
        update_batch_status(db, batch_id)
    record_event(
        db,
        event_type="render_jobs_recovered",
        entity_type="queue",
        entity_id="worker",
        message=f"{len(requeued_ids)} job(s) recuperado(s); {len(canceled_ids)} cancelado(s).",
        payload={"requeued_job_ids": requeued_ids, "canceled_job_ids": canceled_ids},
    )
    return len(jobs)


def update_batch_status(db: Session, batch_id: str) -> None:
    jobs = db.query(RenderJob).filter(RenderJob.batch_id == batch_id).all()
    if not jobs:
        return
    statuses = {job.status for job in jobs}
    batch = db.get(Batch, batch_id)
    if not batch:
        return
    if statuses == {"completed"}:
        batch.status = "completed"
    elif statuses.issubset(TERMINAL_STATUSES):
        batch.status = "completed_with_errors" if "failed" in statuses else "canceled"
    elif (
        batch.is_paused
        and statuses.issubset(TERMINAL_STATUSES | {"processing"})
        and any(job.status == "processing" and job.cancel_requested for job in jobs)
    ):
        batch.status = "canceling"
    elif batch.is_paused:
        batch.status = "pausing" if "processing" in statuses else "paused"
    elif "processing" in statuses:
        batch.status = "processing"
    else:
        batch.status = "queued"
    db.commit()


def process_job(db: Session, job: RenderJob) -> RenderJob:
    job.status = "processing"
    job.progress = 10
    job.current_step = "Preparando receita"
    if job.attempts == 0:
        job.attempts = 1
    if job.started_at is None:
        job.started_at = now_utc()
    job.error_message = None
    db.commit()
    update_batch_status(db, job.batch_id)

    try:
        from .media import existing_asset_path
        recipe = load_recipe(job.template.recipe_json)
        input_path = existing_asset_path(job.asset) or Path(job.asset.stored_path)
        output_root = Path(job.batch.output_dir) if job.batch and job.batch.output_dir else RENDERS_DIR
        output_dir = output_root / job.batch_id
        output_path = output_dir / f"{job.id}.mp4"
        thumbnail_path = THUMBNAILS_DIR / "renders" / f"{job.id}.jpg"

        job.progress = 35
        job.current_step = "Renderizando video 9:16"
        db.commit()

        def should_cancel() -> bool:
            with SessionLocal() as cancel_db:
                requested = cancel_db.execute(
                    select(RenderJob.cancel_requested).where(RenderJob.id == job.id)
                ).scalar_one_or_none()
            return bool(requested)

        render_started = perf_counter()
        metadata = render_video(
            input_path=input_path,
            output_path=output_path,
            thumbnail_path=thumbnail_path,
            recipe=recipe,
            variation_index=job.variation_index,
            should_cancel=should_cancel,
        )
        if should_cancel():
            output_path.unlink(missing_ok=True)
            thumbnail_path.unlink(missing_ok=True)
            raise RenderCanceledError("Render cancelado pelo usuario.")
        render_seconds = max(0.001, perf_counter() - render_started)
        copy_recipe_manifest(recipe, output_dir)

        job.progress = 90
        job.current_step = "Registrando render"
        job.output_path = str(output_path)
        rendered = RenderedVideo(
            job_id=job.id,
            asset_id=job.asset_id,
            template_id=job.template_id,
            path=str(output_path),
            thumbnail_path=str(thumbnail_path) if thumbnail_path.exists() else None,
            duration_seconds=metadata.get("duration_seconds"),
            width=metadata.get("width"),
            height=metadata.get("height"),
            size_bytes=output_path.stat().st_size,
            render_seconds=render_seconds,
            peak_rss_bytes=metadata.get("peak_rss_bytes"),
            status="pending_review",
        )
        db.add(rendered)
        job.status = "completed"
        job.progress = 100
        job.current_step = "Concluido"
        job.finished_at = now_utc()
        job.cancel_requested = False
        db.commit()
        record_event(
            db,
            event_type="render_completed",
            entity_type="render_job",
            entity_id=job.id,
            message=f"Render concluido para {job.asset.filename}.",
            payload={
                "output_path": str(output_path),
                "size_bytes": rendered.size_bytes,
                "render_seconds": round(render_seconds, 3),
                "peak_rss_bytes": rendered.peak_rss_bytes,
            },
        )
    except RenderCanceledError:
        job.status = "canceled"
        job.progress = 100
        job.current_step = "Cancelado"
        job.error_message = None
        job.finished_at = now_utc()
        job.cancel_requested = False
        db.commit()
        record_event(
            db,
            event_type="render_canceled",
            entity_type="render_job",
            entity_id=job.id,
            message="Render em processamento cancelado pelo usuario.",
        )
    except Exception as exc:  # noqa: BLE001
        job.status = "failed"
        job.progress = 100
        job.current_step = "Falhou"
        job.error_message = str(exc)
        job.finished_at = now_utc()
        job.cancel_requested = False
        db.commit()
        record_event(
            db,
            event_type="render_failed",
            entity_type="render_job",
            entity_id=job.id,
            message=str(exc),
            payload={"attempts": job.attempts},
        )
    update_batch_status(db, job.batch_id)
    db.refresh(job)
    return job


def retry_job(db: Session, job: RenderJob, *, reset_attempts: bool = False) -> RenderJob:
    if job.status not in {"failed", "canceled"}:
        raise ValueError("Apenas jobs falhos ou cancelados podem voltar para a fila.")
    _prepare_job_for_retry(job, reset_attempts=reset_attempts)
    db.commit()
    update_batch_status(db, job.batch_id)
    record_event(
        db,
        event_type="render_retried",
        entity_type="render_job",
        entity_id=job.id,
        message="Job recolocado na fila.",
    )
    return job


def _prepare_job_for_retry(job: RenderJob, *, reset_attempts: bool) -> None:
    job.status = "queued"
    job.progress = 0
    job.current_step = "Na fila"
    job.output_path = None
    job.error_message = None
    job.started_at = None
    job.finished_at = None
    job.cancel_requested = False
    if reset_attempts:
        job.attempts = 0


def cancel_job(db: Session, job: RenderJob) -> RenderJob:
    if job.status == "processing":
        if job.cancel_requested:
            job.status = "canceled"
            job.progress = 100
            job.current_step = "Cancelado"
            job.error_message = None
            job.finished_at = now_utc()
            job.cancel_requested = False
            db.commit()
            update_batch_status(db, job.batch_id)
            record_event(
                db,
                event_type="render_canceled",
                entity_type="render_job",
                entity_id=job.id,
                message="Cancelamento forcado pelo usuario.",
            )
            db.refresh(job)
            return job

        job.cancel_requested = True
        job.current_step = "Cancelamento solicitado"
        db.commit()
        record_event(
            db,
            event_type="render_cancel_requested",
            entity_type="render_job",
            entity_id=job.id,
            message="Cancelamento cooperativo solicitado.",
        )
        db.refresh(job)
        return job
    if job.status not in {"queued", "failed"}:
        raise ValueError("Apenas jobs na fila, em processamento ou falhos podem ser cancelados pelo painel.")
    job.status = "canceled"
    job.progress = 100
    job.current_step = "Cancelado"
    job.error_message = None
    job.finished_at = now_utc()
    job.cancel_requested = False
    db.commit()
    update_batch_status(db, job.batch_id)
    record_event(
        db,
        event_type="render_canceled",
        entity_type="render_job",
        entity_id=job.id,
        message="Job cancelado.",
    )
    return job


def cancel_batch(db: Session, batch: Batch) -> Batch:
    jobs = db.query(RenderJob).filter(RenderJob.batch_id == batch.id).all()
    actionable = [job for job in jobs if job.status in {"queued", "processing", "failed"}]
    if not actionable:
        raise ValueError("O lote nao possui jobs ativos ou falhos para cancelar.")

    batch.is_paused = True
    canceled_now = 0
    cancel_requested = 0
    finished_at = now_utc()
    for job in actionable:
        if job.status == "processing":
            job.cancel_requested = True
            job.current_step = "Cancelamento solicitado"
            cancel_requested += 1
            continue
        job.status = "canceled"
        job.progress = 100
        job.current_step = "Cancelado"
        job.error_message = None
        job.finished_at = finished_at
        job.cancel_requested = False
        canceled_now += 1

    db.commit()
    update_batch_status(db, batch.id)
    record_event(
        db,
        event_type="batch_cancel_requested",
        entity_type="batch",
        entity_id=batch.id,
        message=f"Cancelamento do lote solicitado: {canceled_now} job(s) fechado(s), {cancel_requested} ativo(s).",
        payload={"canceled_now": canceled_now, "cancel_requested": cancel_requested},
    )
    db.refresh(batch)
    return batch


def retry_batch(db: Session, batch: Batch, *, reset_attempts: bool = False) -> Batch:
    jobs = db.query(RenderJob).filter(RenderJob.batch_id == batch.id).all()
    if any(job.status == "processing" and job.cancel_requested for job in jobs):
        raise ValueError("Aguarde o cancelamento do job ativo antes de recolocar o lote na fila.")
    retryable = [job for job in jobs if job.status in {"failed", "canceled"}]
    if not retryable:
        raise ValueError("O lote nao possui jobs falhos ou cancelados para repetir.")

    batch.is_paused = False
    for job in retryable:
        _prepare_job_for_retry(job, reset_attempts=reset_attempts)
    db.commit()
    update_batch_status(db, batch.id)
    record_event(
        db,
        event_type="batch_retried",
        entity_type="batch",
        entity_id=batch.id,
        message=f"{len(retryable)} job(s) recolocado(s) na fila.",
        payload={"job_ids": [job.id for job in retryable], "reset_attempts": reset_attempts},
    )
    db.refresh(batch)
    return batch


def pause_batch(db: Session, batch: Batch) -> Batch:
    jobs = db.query(RenderJob).filter(RenderJob.batch_id == batch.id).all()
    if jobs and all(job.status in TERMINAL_STATUSES for job in jobs):
        raise ValueError("Lotes finalizados nao podem ser pausados.")
    batch.is_paused = True
    db.commit()
    update_batch_status(db, batch.id)
    record_event(
        db,
        event_type="batch_paused",
        entity_type="batch",
        entity_id=batch.id,
        message="Lote pausado; o job atual pode terminar antes da pausa completa.",
    )
    db.refresh(batch)
    return batch


def resume_batch(db: Session, batch: Batch) -> Batch:
    jobs = db.query(RenderJob).filter(RenderJob.batch_id == batch.id).all()
    if jobs and all(job.status in TERMINAL_STATUSES for job in jobs):
        raise ValueError("Lotes finalizados nao podem ser retomados.")
    batch.is_paused = False
    db.commit()
    update_batch_status(db, batch.id)
    record_event(
        db,
        event_type="batch_resumed",
        entity_type="batch",
        entity_id=batch.id,
        message="Lote retomado e liberado para o worker.",
    )
    db.refresh(batch)
    return batch
