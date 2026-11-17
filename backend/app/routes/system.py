from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import ALLOWED_OUTPUT_ROOTS, DATABASE_PATH, DB_DIR, IMPORT_ROOTS, SETTINGS_FILE
from ..database import database_status, get_db
from ..models import Asset, AuditEvent, Batch, BrandKit, ClipCandidate, PublishTask, RenderJob, RenderedVideo, Template
from ..schemas import SettingsUpdateRequest, StorageCheckRequest, TestGoogleApiRequest, TtsSynthesizeRequest
from ..serializers import audit_to_dict
from ..services.audit import record_event
from ..services.media import ffmpeg_status
from ..services.path_policy import resolve_allowed_directory
from ..services.render_metrics import render_performance_snapshot
from ..services.storage import check_storage_capacity

router = APIRouter(prefix="/api/system", tags=["system"])


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    try:
        for entry in path.rglob("*"):
            if entry.is_file():
                total += entry.stat().st_size
    except Exception:
        pass
    return total


@router.get("/health")
def health(db: Session = Depends(get_db)):
    from .. import config
    return {
        "status": "ok",
        "ffmpeg": ffmpeg_status(),
        "import_roots": [str(root) for root in IMPORT_ROOTS],
        "database": {
            "path": str(DATABASE_PATH),
            **database_status(db),
        },
        "allowed_output_roots": [str(root) for root in ALLOWED_OUTPUT_ROOTS],
        "storage": {
            "data_dir": str(config.DATA_DIR),
            "assets_bytes": _dir_size(config.ASSETS_DIR),
            "renders_bytes": _dir_size(config.RENDERS_DIR),
            "proxies_bytes": _dir_size(config.PROXIES_DIR),
            "thumbnails_bytes": _dir_size(config.THUMBNAILS_DIR),
            "publish_packages_bytes": _dir_size(config.PUBLISH_PACKAGES_DIR),
            "db_bytes": _dir_size(config.DB_DIR),
            "logs_bytes": _dir_size(config.LOGS_DIR),
            "total_bytes": _dir_size(config.DATA_DIR),
        },
        "counts": {
            "assets": db.query(Asset).count(),
            "templates": db.query(Template).count(),
            "batches": db.query(Batch).count(),
            "jobs": db.query(RenderJob).count(),
            "renders": db.query(RenderedVideo).count(),
            "publish_tasks": db.query(PublishTask).count(),
            "brand_kits": db.query(BrandKit).count(),
            "clip_candidates": db.query(ClipCandidate).count(),
        },
        "queue": {
            "queued": db.query(RenderJob).filter(RenderJob.status == "queued").count(),
            "processing": db.query(RenderJob).filter(RenderJob.status == "processing").count(),
            "completed": db.query(RenderJob).filter(RenderJob.status == "completed").count(),
            "failed": db.query(RenderJob).filter(RenderJob.status == "failed").count(),
            "canceled": db.query(RenderJob).filter(RenderJob.status == "canceled").count(),
        },
        "render_performance": render_performance_snapshot(db),
    }


@router.post("/storage-check")
def storage_check(payload: StorageCheckRequest):
    return check_storage_capacity(payload.output_dir, payload.estimated_output_bytes)


@router.post("/backup")
def backup_database(db: Session = Depends(get_db)):
    DB_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    target = DB_DIR / f"video_os-{stamp}.sqlite3"
    db.commit()
    with sqlite3.connect(DATABASE_PATH) as source, sqlite3.connect(target) as destination:
        source.backup(destination)
    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "database": str(target),
        "method": "sqlite_backup_api",
        "size_bytes": target.stat().st_size,
    }
    manifest_path = DB_DIR / f"video_os-{stamp}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    record_event(
        db,
        event_type="backup_created",
        entity_type="database",
        entity_id=target.name,
        message="Backup local criado.",
        payload=manifest,
    )
    return manifest


@router.get("/audit")
def list_audit(db: Session = Depends(get_db)):
    events = db.query(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(100).all()
    return [audit_to_dict(event) for event in events]


@router.get("/logs")
def list_logs():
    from .. import config
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logs = []
    total_bytes = 0
    for file_path in sorted(config.LOGS_DIR.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True):
        size = file_path.stat().st_size
        total_bytes += size
        logs.append({
            "filename": file_path.name,
            "size_bytes": size,
            "modified_at": datetime.fromtimestamp(file_path.stat().st_mtime, UTC).isoformat(),
        })
    return {
        "logs_dir": str(config.LOGS_DIR),
        "total_files": len(logs),
        "total_bytes": total_bytes,
        "files": logs,
    }


@router.post("/logs/purge")
def purge_logs(keep_latest: int = 10, db: Session = Depends(get_db)):
    from .. import config
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    all_logs = sorted(config.LOGS_DIR.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    to_delete = all_logs[keep_latest:] if len(all_logs) > keep_latest else []
    deleted_count = 0
    reclaimed_bytes = 0

    for file_path in to_delete:
        try:
            size = file_path.stat().st_size
            file_path.unlink()
            deleted_count += 1
            reclaimed_bytes += size
        except Exception:
            pass

    record_event(
        db,
        event_type="logs_purged",
        entity_type="system",
        entity_id="logs",
        message=f"{deleted_count} logs purgados. {reclaimed_bytes} bytes liberados.",
        payload={"deleted_count": deleted_count, "reclaimed_bytes": reclaimed_bytes, "kept": keep_latest},
    )

    return {
        "deleted_count": deleted_count,
        "reclaimed_bytes": reclaimed_bytes,
        "remaining_count": len(all_logs) - deleted_count,
    }


@router.post("/open-path")
def open_system_path(payload: dict[str, str], db: Session = Depends(get_db)):
    import os
    import sys
    from ..config import path_is_within_roots

    raw_path = payload.get("path", "").strip()
    if not raw_path:
        raise HTTPException(status_code=400, detail="Caminho obrigatorio.")

    target = Path(raw_path).resolve()
    if not target.exists():
        raise HTTPException(status_code=404, detail="Arquivo ou pasta nao encontrado.")

    if not path_is_within_roots(target):
        raise HTTPException(status_code=403, detail="Acesso ao caminho nao permitido fora das raizes do sistema.")

    folder_to_open = target if target.is_dir() else target.parent

    try:
        if sys.platform == "win32":
            os.startfile(str(folder_to_open))
        else:
            import subprocess
            subprocess.Popen(["xdg-open", str(folder_to_open)])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Falha ao abrir pasta: {exc}")

    record_event(
        db,
        event_type="path_opened",
        entity_type="system",
        entity_id="explorer",
        message=f"Pasta aberta no gerenciador de arquivos: {folder_to_open}",
        payload={"path": str(folder_to_open)},
    )

    return {"success": True, "opened_path": str(folder_to_open)}


def to_display_path(path_str: str) -> str:
    m = re.match(r"^/host/([a-zA-Z])/(.*)$", path_str)
    if m:
        drive = m.group(1).upper()
        rest = m.group(2).replace("/", "\\")
        return f"{drive}:\\{rest}"
    return path_str


@router.get("/settings")
def get_settings():
    from .. import config
    masked_key = ""
    if config.GOOGLE_API_KEY:
        masked_key = (
            f"{config.GOOGLE_API_KEY[:6]}...{config.GOOGLE_API_KEY[-4:]}"
            if len(config.GOOGLE_API_KEY) > 10
            else "******"
        )
    return {
        "incoming_dir": to_display_path(str(config.INCOMING_DIR)),
        "assets_dir": to_display_path(str(config.ASSETS_DIR)),
        "renders_dir": to_display_path(str(config.RENDERS_DIR)),
        "publish_packages_dir": to_display_path(str(config.PUBLISH_PACKAGES_DIR)),
        "allowed_output_roots": [to_display_path(str(root)) for root in ALLOWED_OUTPUT_ROOTS],
        "google_api_key_configured": bool(config.GOOGLE_API_KEY),
        "google_api_key_masked": masked_key,
        "gemini_model": config.GEMINI_MODEL,
    }


@router.post("/settings")
def update_settings(payload: SettingsUpdateRequest, db: Session = Depends(get_db)):
    from .. import config
    
    custom = {}
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                custom = json.load(f)
        except Exception:
            pass
            
    if payload.incoming_dir is not None:
        custom["incoming_dir"] = str(resolve_allowed_directory(payload.incoming_dir, field_name="incoming_dir"))
    if payload.assets_dir is not None:
        custom["assets_dir"] = str(resolve_allowed_directory(payload.assets_dir, field_name="assets_dir"))
    if payload.renders_dir is not None:
        custom["renders_dir"] = str(resolve_allowed_directory(payload.renders_dir, field_name="renders_dir"))
    if payload.publish_packages_dir is not None:
        custom["publish_packages_dir"] = str(
            resolve_allowed_directory(payload.publish_packages_dir, field_name="publish_packages_dir")
        )
    if payload.google_api_key is not None:
        custom["google_api_key"] = payload.google_api_key.strip()
    if payload.gemini_model is not None:
        custom["gemini_model"] = payload.gemini_model.strip()
        
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(custom, f, ensure_ascii=False, indent=2)
        
    config.load_custom_settings()
    config.ensure_data_dirs()
    
    record_event(
        db,
        event_type="settings_updated",
        entity_type="system",
        entity_id="settings",
        message="Destinos de pastas e parâmetros de IA atualizados.",
        payload={"google_api_key_configured": bool(config.GOOGLE_API_KEY), "gemini_model": config.GEMINI_MODEL},
    )
    
    return get_settings()


@router.post("/settings/reset")
def reset_settings(db: Session = Depends(get_db)):
    from .. import config
    if SETTINGS_FILE.exists():
        try:
            SETTINGS_FILE.unlink()
        except Exception:
            pass

    config.INCOMING_DIR = config.DATA_DIR / "incoming"
    config.ASSETS_DIR = config.DATA_DIR / "assets"
    config.RENDERS_DIR = config.DATA_DIR / "renders"
    config.THUMBNAILS_DIR = config.DATA_DIR / "thumbnails"
    config.PUBLISH_PACKAGES_DIR = config.DATA_DIR / "publish-packages"
    config.TRANSCRIPTS_DIR = config.DATA_DIR / "transcripts"
    config.PROXIES_DIR = config.DATA_DIR / "proxies"
    config.DB_DIR = config.DATA_DIR / "db"
    config.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", "")).strip()
    config.GEMINI_MODEL = os.getenv("VIDEO_OS_GEMINI_MODEL", "gemini-2.0-flash").strip()
    config.ensure_data_dirs()

    record_event(
        db,
        event_type="settings_reset",
        entity_type="system",
        entity_id="settings",
        message="Destinos de pastas e parâmetros restaurados para o padrao.",
        payload={},
    )
    return get_settings()


@router.get("/ai-status")
def get_ai_status():
    from ..services.llm import get_ai_providers_status
    return get_ai_providers_status()


@router.post("/test-google-api")
def test_google_api(payload: TestGoogleApiRequest):
    from ..services.llm import test_google_connection
    return test_google_connection(payload.api_key, payload.model)


@router.get("/tts/voices")
def get_tts_voices():
    from ..services.tts import list_voices
    return list_voices()


@router.post("/tts/synthesize")
def post_tts_synthesize(payload: TtsSynthesizeRequest):
    from ..services.tts import synthesize_speech
    try:
        return synthesize_speech(payload.text, payload.voice)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Falha na sintese de voz: {exc}")
