from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import PlatformPreset, PublishTask, RenderedVideo
from ..schemas import PublishPackageRequest, PublishTaskUpdate
from ..serializers import preset_to_dict, publish_task_to_dict
from ..services.audit import record_event
from ..services.path_policy import resolve_allowed_directory
from ..services.publisher import generate_package
from ..services.quality import analyze_render

router = APIRouter(prefix="/api", tags=["publishing"])


@router.get("/platform-presets")
def list_platform_presets(db: Session = Depends(get_db)):
    presets = db.query(PlatformPreset).order_by(PlatformPreset.platform.asc()).all()
    return [preset_to_dict(preset) for preset in presets]


@router.get("/publish-tasks")
def list_publish_tasks(db: Session = Depends(get_db)):
    tasks = db.query(PublishTask).order_by(PublishTask.created_at.desc()).all()
    return [publish_task_to_dict(task) for task in tasks]


@router.get("/publish-tasks/{task_id}/quality-report")
def download_publish_quality_report(task_id: str, db: Session = Depends(get_db)):
    task = db.get(PublishTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa de publicacao nao encontrada.")
    package_dir = resolve_allowed_directory(task.package_dir, field_name="package_dir")
    report_path = (package_dir / "quality-report.json").resolve()
    if report_path.parent != package_dir:
        raise HTTPException(status_code=400, detail="quality-report.json fora do pacote permitido.")
    if not report_path.is_file():
        raise HTTPException(status_code=404, detail="Relatorio de qualidade nao encontrado no pacote.")
    return FileResponse(
        path=report_path,
        media_type="application/json",
        filename=f"quality-report-{task.platform}-{task.id[:8]}.json",
    )


@router.post("/publish-packages")
def create_publish_packages(payload: PublishPackageRequest, db: Session = Depends(get_db)):
    rendered_items = db.query(RenderedVideo).filter(RenderedVideo.id.in_(payload.rendered_video_ids)).all()
    if len(rendered_items) != len(set(payload.rendered_video_ids)):
        raise HTTPException(status_code=404, detail="Um ou mais renders nao foram encontrados.")
    tasks: list[PublishTask] = []
    for rendered in rendered_items:
        if rendered.status != "approved":
            raise HTTPException(
                status_code=422,
                detail=f"Render {rendered.id} precisa estar aprovado antes do pacote.",
            )
        technical_metadata, _analysis_cache = analyze_render(db, rendered)
        for platform in payload.platforms:
            tasks.append(
                generate_package(
                    db,
                    rendered=rendered,
                    platform=platform,
                    caption=payload.caption,
                    hashtags=payload.hashtags,
                    output_dir=payload.output_dir,
                    technical_metadata=technical_metadata,
                )
            )
    return {"created": [publish_task_to_dict(task) for task in tasks], "count": len(tasks)}


@router.patch("/publish-tasks/{task_id}")
def update_publish_task(task_id: str, payload: PublishTaskUpdate, db: Session = Depends(get_db)):
    task = db.get(PublishTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa de publicacao nao encontrada.")
    task.status = payload.status
    db.commit()
    db.refresh(task)
    record_event(
        db,
        event_type="publish_task_updated",
        entity_type="publish_task",
        entity_id=task.id,
        message=f"Status de publicacao alterado para {task.status}.",
    )
    return publish_task_to_dict(task)


@router.patch("/publish-tasks/{task_id}/checklist")
def update_publish_task_checklist(task_id: str, payload: dict, db: Session = Depends(get_db)):
    task = db.get(PublishTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa de publicacao nao encontrada.")
    if "checklist" in payload:
        import json
        task.checklist_json = json.dumps(payload["checklist"], ensure_ascii=False)
    db.commit()
    db.refresh(task)
    return publish_task_to_dict(task)


@router.post("/publish-tasks/{task_id}/open-folder")
def open_publish_package_folder(task_id: str, db: Session = Depends(get_db)):
    import os
    import subprocess
    task = db.get(PublishTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa de publicacao nao encontrada.")
    pkg_path = resolve_allowed_directory(task.package_dir, field_name="package_dir")
    if not pkg_path.exists():
        raise HTTPException(status_code=404, detail="Diretorio do pacote nao encontrado.")
    if os.name == "nt":
        subprocess.Popen(["explorer", str(pkg_path)])
    return {"status": "success", "package_dir": str(pkg_path)}

