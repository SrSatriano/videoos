from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import IMPORT_ROOTS
from app.database import SessionLocal
from app.main import app
from app.models import RenderJob, RenderedVideo
from app.services.queue import RenderCanceledError, claim_next_job, process_job, recover_interrupted_jobs

from conftest import DATA_ROOT


client = TestClient(app)


def test_batch_creation_creates_ten_variations() -> None:
    video_path = IMPORT_ROOTS[0] / "batch-source.mp4"
    video_path.write_bytes(b"batch bytes")

    imported = client.post("/api/assets/import", json={"paths": [str(video_path)], "copy_to_library": True})
    template = client.get("/api/templates").json()[0]
    asset = imported.json()["imported"][0]

    response = client.post(
        "/api/batches",
        json={
            "name": "Lote com 10 variacoes",
            "template_id": template["id"],
            "asset_ids": [asset["id"]],
            "variations": 10,
        },
    )
    jobs = client.get("/api/jobs").json()

    assert response.status_code == 200
    assert response.json()["total_jobs"] == 10
    assert sum(1 for job in jobs if job["batch_id"] == response.json()["id"]) == 10


def test_batch_creation_accepts_output_dir_inside_allowed_roots() -> None:
    video_path = IMPORT_ROOTS[0] / "batch-output-source.mp4"
    output_dir = DATA_ROOT / "batch-renders"
    video_path.write_bytes(b"batch output bytes")

    imported = client.post("/api/assets/import", json={"paths": [str(video_path)], "copy_to_library": True})
    template = client.get("/api/templates").json()[0]
    asset = imported.json()["imported"][0]

    response = client.post(
        "/api/batches",
        json={
            "name": "Lote com saida propria",
            "template_id": template["id"],
            "asset_ids": [asset["id"]],
            "variations": 1,
            "output_dir": str(output_dir),
        },
    )

    assert response.status_code == 200
    assert response.json()["output_dir"] == str(output_dir.resolve())


def test_batch_creation_rejects_insufficient_safe_storage(monkeypatch) -> None:
    video_path = IMPORT_ROOTS[0] / "batch-storage-source.mp4"
    video_path.write_bytes(b"batch storage bytes")
    imported = client.post("/api/assets/import", json={"paths": [str(video_path)], "copy_to_library": True})
    template = client.get("/api/templates").json()[0]
    asset = imported.json()["imported"][0]

    monkeypatch.setattr(
        "app.services.queue.check_storage_capacity",
        lambda _path, estimate: {
            "estimated_output_bytes": estimate,
            "required_bytes": 2_000,
            "safe_available_bytes": 1_000,
            "has_capacity": False,
        },
    )

    response = client.post(
        "/api/batches",
        json={
            "name": "Lote sem espaco seguro",
            "template_id": template["id"],
            "asset_ids": [asset["id"]],
            "variations": 1,
            "estimated_output_bytes": 1_500,
        },
    )

    assert response.status_code == 422
    assert "Espaco seguro insuficiente" in response.json()["detail"]


def test_batch_process_uses_custom_output_dir(monkeypatch) -> None:
    video_path = IMPORT_ROOTS[0] / "batch-process-output-source.mp4"
    output_dir = DATA_ROOT / "process-renders"
    video_path.write_bytes(b"batch process bytes")
    rendered_paths: list[str] = []

    def fake_render_video(*, output_path, thumbnail_path, **_kwargs):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"rendered")
        thumbnail_path.write_bytes(b"thumbnail")
        rendered_paths.append(str(output_path))
        return {
            "duration_seconds": 12,
            "width": 1080,
            "height": 1920,
            "peak_rss_bytes": 456_789,
        }

    import app.services.queue as queue_service

    monkeypatch.setattr(queue_service, "render_video", fake_render_video)

    imported = client.post("/api/assets/import", json={"paths": [str(video_path)], "copy_to_library": True})
    template = client.get("/api/templates").json()[0]
    asset = imported.json()["imported"][0]
    batch = client.post(
        "/api/batches",
        json={
            "name": "Lote processa saida propria",
            "template_id": template["id"],
            "asset_ids": [asset["id"]],
            "variations": 1,
            "output_dir": str(output_dir),
        },
    ).json()

    with SessionLocal() as db:
        db.query(RenderJob).filter(RenderJob.batch_id != batch["id"], RenderJob.status == "queued").update(
            {"status": "canceled"},
            synchronize_session=False,
        )
        db.commit()

    response = client.post("/api/jobs/process-next")

    assert response.status_code == 200
    assert response.json()["processed"]["status"] == "completed"
    assert len(rendered_paths) == 1
    assert rendered_paths[0].startswith(str((output_dir / batch["id"]).resolve()))
    with SessionLocal() as db:
        rendered = db.query(RenderedVideo).filter(RenderedVideo.job_id == response.json()["processed"]["id"]).one()
        assert rendered.size_bytes == len(b"rendered")
        assert rendered.render_seconds is not None
        assert rendered.render_seconds > 0
        assert rendered.peak_rss_bytes == 456_789


def test_recover_interrupted_jobs_returns_processing_jobs_to_queue() -> None:
    video_path = IMPORT_ROOTS[0] / "recover-source.mp4"
    video_path.write_bytes(b"recover bytes")

    imported = client.post("/api/assets/import", json={"paths": [str(video_path)], "copy_to_library": True})
    template = client.get("/api/templates").json()[0]
    asset = imported.json()["imported"][0]
    batch = client.post(
        "/api/batches",
        json={
            "name": "Lote recuperavel",
            "template_id": template["id"],
            "asset_ids": [asset["id"]],
            "variations": 1,
        },
    ).json()

    with SessionLocal() as db:
        job = db.query(RenderJob).filter(RenderJob.batch_id == batch["id"]).one()
        job.status = "processing"
        job.progress = 35
        job.current_step = "Renderizando video 9:16"
        db.commit()

        recovered = recover_interrupted_jobs(db)
        db.refresh(job)

        assert recovered >= 1
        assert job.status == "queued"
        assert job.progress == 0
        assert "Recuperado" in job.current_step


def test_claim_next_job_is_atomic_for_single_job() -> None:
    video_path = IMPORT_ROOTS[0] / "claim-source.mp4"
    video_path.write_bytes(b"claim bytes")

    imported = client.post("/api/assets/import", json={"paths": [str(video_path)], "copy_to_library": True})
    template = client.get("/api/templates").json()[0]
    asset = imported.json()["imported"][0]
    batch = client.post(
        "/api/batches",
        json={
            "name": "Lote claim",
            "template_id": template["id"],
            "asset_ids": [asset["id"]],
            "variations": 1,
        },
    ).json()

    with SessionLocal() as db:
        db.query(RenderJob).filter(RenderJob.batch_id != batch["id"], RenderJob.status == "queued").update(
            {"status": "canceled"},
            synchronize_session=False,
        )
        db.commit()

    with SessionLocal() as first_db:
        first = claim_next_job(first_db)
        first_batch_id = first.batch_id if first else None
        first_status = first.status if first else None
        first_attempts = first.attempts if first else None
    with SessionLocal() as second_db:
        second = claim_next_job(second_db)

    assert first is not None
    assert first_batch_id == batch["id"]
    assert first_status == "processing"
    assert first_attempts == 1
    assert second is None


def test_paused_batch_is_not_claimed_and_resume_preserves_queue() -> None:
    video_path = IMPORT_ROOTS[0] / "pause-source.mp4"
    video_path.write_bytes(b"pause bytes")
    imported = client.post("/api/assets/import", json={"paths": [str(video_path)], "copy_to_library": True})
    template = client.get("/api/templates").json()[0]
    asset = imported.json()["imported"][0]
    batch = client.post(
        "/api/batches",
        json={
            "name": "Lote pausavel",
            "template_id": template["id"],
            "asset_ids": [asset["id"]],
            "variations": 1,
        },
    ).json()

    with SessionLocal() as db:
        db.query(RenderJob).filter(RenderJob.batch_id != batch["id"], RenderJob.status == "queued").update(
            {"status": "canceled"},
            synchronize_session=False,
        )
        db.commit()

    paused = client.post(f"/api/batches/{batch['id']}/pause")
    assert paused.status_code == 200
    assert paused.json()["is_paused"] is True
    assert paused.json()["status"] == "paused"
    with SessionLocal() as db:
        assert claim_next_job(db) is None

    resumed = client.post(f"/api/batches/{batch['id']}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["is_paused"] is False
    assert resumed.json()["status"] == "queued"
    with SessionLocal() as db:
        claimed = claim_next_job(db)
        assert claimed is not None
        assert claimed.batch_id == batch["id"]


def test_processing_cancel_request_recovers_as_canceled() -> None:
    video_path = IMPORT_ROOTS[0] / "cancel-processing-source.mp4"
    video_path.write_bytes(b"cancel processing bytes")
    imported = client.post("/api/assets/import", json={"paths": [str(video_path)], "copy_to_library": True})
    template = client.get("/api/templates").json()[0]
    asset = imported.json()["imported"][0]
    batch = client.post(
        "/api/batches",
        json={
            "name": "Lote cancelavel",
            "template_id": template["id"],
            "asset_ids": [asset["id"]],
            "variations": 1,
        },
    ).json()

    with SessionLocal() as db:
        job = db.query(RenderJob).filter(RenderJob.batch_id == batch["id"]).one()
        job.status = "processing"
        job.progress = 35
        db.commit()
        job_id = job.id

    requested = client.post(f"/api/jobs/{job_id}/cancel")
    assert requested.status_code == 200
    assert requested.json()["status"] == "processing"
    assert requested.json()["cancel_requested"] is True
    assert requested.json()["current_step"] == "Cancelamento solicitado"

    with SessionLocal() as db:
        recovered = recover_interrupted_jobs(db)
        job = db.get(RenderJob, job_id)
        assert recovered >= 1
        assert job is not None
        assert job.status == "canceled"
        assert job.cancel_requested is False


def test_process_job_records_cooperative_cancel_without_render(monkeypatch) -> None:
    video_path = IMPORT_ROOTS[0] / "cooperative-cancel-source.mp4"
    video_path.write_bytes(b"cooperative cancel bytes")
    imported = client.post("/api/assets/import", json={"paths": [str(video_path)], "copy_to_library": True})
    template = client.get("/api/templates").json()[0]
    asset = imported.json()["imported"][0]
    batch = client.post(
        "/api/batches",
        json={
            "name": "Lote cooperativo",
            "template_id": template["id"],
            "asset_ids": [asset["id"]],
            "variations": 1,
        },
    ).json()

    def canceled_render(*, should_cancel, **_kwargs):
        assert should_cancel() is False
        raise RenderCanceledError("Render cancelado pelo usuario.")

    monkeypatch.setattr("app.services.queue.render_video", canceled_render)
    with SessionLocal() as db:
        job = db.query(RenderJob).filter(RenderJob.batch_id == batch["id"]).one()
        processed = process_job(db, job)
        assert processed.status == "canceled"
        assert processed.current_step == "Cancelado"
        assert processed.error_message is None
        assert db.query(RenderedVideo).filter(RenderedVideo.job_id == job.id).count() == 0


def test_cancel_batch_stops_pending_jobs_and_requests_active_cancel() -> None:
    video_path = IMPORT_ROOTS[0] / "cancel-batch-source.mp4"
    video_path.write_bytes(b"cancel batch bytes")
    imported = client.post("/api/assets/import", json={"paths": [str(video_path)], "copy_to_library": True})
    template = client.get("/api/templates").json()[0]
    asset = imported.json()["imported"][0]
    batch = client.post(
        "/api/batches",
        json={
            "name": "Lote cancelado em massa",
            "template_id": template["id"],
            "asset_ids": [asset["id"]],
            "variations": 3,
        },
    ).json()

    with SessionLocal() as db:
        jobs = db.query(RenderJob).filter(RenderJob.batch_id == batch["id"]).order_by(RenderJob.variation_index).all()
        jobs[0].status = "processing"
        jobs[0].progress = 35
        jobs[1].status = "failed"
        jobs[1].progress = 100
        jobs[1].attempts = 2
        db.commit()

    response = client.post(f"/api/batches/{batch['id']}/cancel")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "canceling"
    assert payload["is_paused"] is True
    assert payload["active_jobs"] == 1
    assert payload["canceled_jobs"] == 2
    assert payload["retryable_jobs"] == 2
    with SessionLocal() as db:
        jobs = db.query(RenderJob).filter(RenderJob.batch_id == batch["id"]).order_by(RenderJob.variation_index).all()
        assert jobs[0].status == "processing"
        assert jobs[0].cancel_requested is True
        assert jobs[1].status == "canceled"
        assert jobs[2].status == "canceled"

        recover_interrupted_jobs(db)
        db.refresh(jobs[0])
        assert jobs[0].status == "canceled"

    finished = next(item for item in client.get("/api/batches").json() if item["id"] == batch["id"])
    assert finished["status"] == "canceled"
    assert finished["active_jobs"] == 0
    assert finished["canceled_jobs"] == 3


def test_retry_batch_requeues_only_failed_and_canceled_jobs() -> None:
    video_path = IMPORT_ROOTS[0] / "retry-batch-source.mp4"
    video_path.write_bytes(b"retry batch bytes")
    imported = client.post("/api/assets/import", json={"paths": [str(video_path)], "copy_to_library": True})
    template = client.get("/api/templates").json()[0]
    asset = imported.json()["imported"][0]
    batch = client.post(
        "/api/batches",
        json={
            "name": "Lote retomado em massa",
            "template_id": template["id"],
            "asset_ids": [asset["id"]],
            "variations": 3,
        },
    ).json()

    with SessionLocal() as db:
        jobs = db.query(RenderJob).filter(RenderJob.batch_id == batch["id"]).order_by(RenderJob.variation_index).all()
        jobs[0].status = "completed"
        jobs[0].progress = 100
        jobs[1].status = "failed"
        jobs[1].progress = 100
        jobs[1].attempts = 3
        jobs[1].error_message = "falha controlada"
        jobs[2].status = "canceled"
        jobs[2].progress = 100
        jobs[2].attempts = 2
        db.commit()

    response = client.post(f"/api/batches/{batch['id']}/retry", json={"reset_attempts": True})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["is_paused"] is False
    assert payload["completed_jobs"] == 1
    assert payload["active_jobs"] == 2
    assert payload["retryable_jobs"] == 0
    with SessionLocal() as db:
        jobs = db.query(RenderJob).filter(RenderJob.batch_id == batch["id"]).order_by(RenderJob.variation_index).all()
        assert jobs[0].status == "completed"
        assert jobs[1].status == "queued"
        assert jobs[2].status == "queued"
        assert jobs[1].attempts == 0
        assert jobs[2].attempts == 0
        assert jobs[1].error_message is None
        assert jobs[2].finished_at is None


def test_clip_candidate_can_create_trimmed_batch() -> None:
    video_path = IMPORT_ROOTS[0] / "clip-batch-source.mp4"
    video_path.write_bytes(b"clip batch bytes")

    imported = client.post("/api/assets/import", json={"paths": [str(video_path)], "copy_to_library": True})
    template = client.get("/api/templates").json()[0]
    asset = imported.json()["imported"][0]
    clips = client.post(
        "/api/clips/analyze",
        json={"asset_id": asset["id"], "min_seconds": 10, "max_seconds": 35, "limit": 1},
    ).json()

    response = client.post(
        f"/api/clips/{clips[0]['id']}/create-batch",
        json={"template_id": template["id"], "name": "Lote do corte", "variations": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["batch"]["total_jobs"] == 2
    assert payload["template"]["recipe"]["trim"]["start"] == clips[0]["start_seconds"]
    assert payload["template"]["recipe"]["trim"]["end"] == clips[0]["end_seconds"]


def test_process_next_job_prevents_concurrent_processing() -> None:
    video_path = IMPORT_ROOTS[0] / "concur-source.mp4"
    video_path.write_bytes(b"concur bytes")
    imported = client.post("/api/assets/import", json={"paths": [str(video_path)], "copy_to_library": True})
    template = client.get("/api/templates").json()[0]
    asset = imported.json()["imported"][0]
    batch = client.post(
        "/api/batches",
        json={
            "name": "Lote concorrencia",
            "template_id": template["id"],
            "asset_ids": [asset["id"]],
            "variations": 2,
        },
    ).json()

    with SessionLocal() as db:
        job = db.query(RenderJob).filter(RenderJob.batch_id == batch["id"]).first()
        assert job is not None
        job.status = "processing"
        db.commit()

    response = client.post("/api/jobs/process-next")
    assert response.status_code == 200
    assert response.json()["processed"] is None
    assert "Ja existe um job em processamento" in response.json()["message"]

