from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import DATA_DIR
from .models import (
    Asset,
    AssetProxy,
    AuditEvent,
    Batch,
    PlatformPreset,
    PublishTask,
    RenderJob,
    RenderedVideo,
    SceneMarker,
    Template,
    Transcript,
    ScheduleSlot,
)



def media_url(path_value: str | None) -> str | None:
    if not path_value:
        return None
    path = Path(path_value)
    try:
        relative = path.resolve().relative_to(DATA_DIR.resolve())
    except ValueError:
        return None
    return "/media/" + relative.as_posix()


def asset_to_dict(asset: Asset) -> dict[str, Any]:
    return {
        "id": asset.id,
        "filename": asset.filename,
        "original_path": asset.original_path,
        "stored_path": asset.stored_path,
        "sha256": asset.sha256,
        "size_bytes": asset.size_bytes,
        "duration_seconds": asset.duration_seconds,
        "width": asset.width,
        "height": asset.height,
        "fps": asset.fps,
        "orientation": asset.orientation,
        "metadata_status": asset.metadata_status,
        "thumbnail_url": media_url(asset.thumbnail_path),
        "media_url": media_url(asset.stored_path),
        "created_at": asset.created_at.isoformat(),
    }


def proxy_to_dict(proxy: AssetProxy) -> dict[str, Any]:
    return {
        "id": proxy.id,
        "asset_id": proxy.asset_id,
        "path": proxy.path,
        "media_url": media_url(proxy.path),
        "width": proxy.width,
        "height": proxy.height,
        "size_bytes": proxy.size_bytes,
        "status": proxy.status,
        "error_message": proxy.error_message,
        "created_at": proxy.created_at.isoformat(),
        "updated_at": proxy.updated_at.isoformat(),
    }


def marker_to_dict(marker: SceneMarker) -> dict[str, Any]:
    return {
        "id": marker.id,
        "asset_id": marker.asset_id,
        "time_seconds": marker.time_seconds,
        "duration_seconds": marker.duration_seconds,
        "label": marker.label,
        "color": marker.color,
        "marker_type": marker.marker_type,
        "source": marker.source,
        "notes": marker.notes,
        "created_at": marker.created_at.isoformat(),
    }


def template_to_dict(template: Template) -> dict[str, Any]:
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "recipe": json.loads(template.recipe_json),
        "created_at": template.created_at.isoformat(),
        "updated_at": template.updated_at.isoformat(),
    }


def batch_to_dict(batch: Batch) -> dict[str, Any]:
    completed = sum(1 for job in batch.jobs if job.status == "completed")
    failed = sum(1 for job in batch.jobs if job.status == "failed")
    canceled = sum(1 for job in batch.jobs if job.status == "canceled")
    active = sum(1 for job in batch.jobs if job.status in {"queued", "processing"})
    return {
        "id": batch.id,
        "name": batch.name,
        "template_id": batch.template_id,
        "status": batch.status,
        "total_jobs": batch.total_jobs,
        "completed_jobs": completed,
        "failed_jobs": failed,
        "canceled_jobs": canceled,
        "active_jobs": active,
        "retryable_jobs": failed + canceled,
        "output_dir": batch.output_dir,
        "is_paused": bool(batch.is_paused),
        "created_at": batch.created_at.isoformat(),
    }


def job_to_dict(job: RenderJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "batch_id": job.batch_id,
        "asset_id": job.asset_id,
        "template_id": job.template_id,
        "variation_index": job.variation_index,
        "status": job.status,
        "progress": job.progress,
        "current_step": job.current_step,
        "output_path": job.output_path,
        "output_url": media_url(job.output_path),
        "error_message": job.error_message,
        "attempts": job.attempts,
        "cancel_requested": bool(job.cancel_requested),
        "asset_filename": job.asset.filename if job.asset else None,
        "template_name": job.template.name if job.template else None,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }


def rendered_to_dict(rendered: RenderedVideo) -> dict[str, Any]:
    return {
        "id": rendered.id,
        "job_id": rendered.job_id,
        "asset_id": rendered.asset_id,
        "template_id": rendered.template_id,
        "path": rendered.path,
        "media_url": media_url(rendered.path),
        "thumbnail_url": media_url(rendered.thumbnail_path),
        "duration_seconds": rendered.duration_seconds,
        "width": rendered.width,
        "height": rendered.height,
        "size_bytes": rendered.size_bytes,
        "render_seconds": rendered.render_seconds,
        "peak_rss_bytes": rendered.peak_rss_bytes,
        "status": rendered.status,
        "created_at": rendered.created_at.isoformat(),
        "reviewed_at": rendered.reviewed_at.isoformat() if rendered.reviewed_at else None,
    }


def preset_to_dict(preset: PlatformPreset) -> dict[str, Any]:
    try:
        safe_zone = json.loads(preset.safe_zone_json)
    except json.JSONDecodeError:
        safe_zone = {}
    return {
        "id": preset.id,
        "platform": preset.platform,
        "label": preset.label,
        "width": preset.width,
        "height": preset.height,
        "codec": preset.codec,
        "checklist": json.loads(preset.checklist_json),
        "rule_type": preset.rule_type,
        "source_url": preset.source_url,
        "source_checked_at": preset.source_checked_at,
        "max_duration_seconds": preset.max_duration_seconds,
        "max_file_size_mb": preset.max_file_size_mb,
        "min_width": preset.min_width,
        "min_height": preset.min_height,
        "min_bitrate_kbps": preset.min_bitrate_kbps,
        "safe_zone": safe_zone,
        "notes": preset.notes,
    }


def publish_task_to_dict(task: PublishTask) -> dict[str, Any]:
    return {
        "id": task.id,
        "rendered_video_id": task.rendered_video_id,
        "platform": task.platform,
        "status": task.status,
        "package_dir": task.package_dir,
        "caption": task.caption,
        "hashtags": json.loads(task.hashtags_json),
        "checklist": json.loads(task.checklist_json),
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }


def audit_to_dict(event: AuditEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "event_type": event.event_type,
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "message": event.message,
        "payload": json.loads(event.payload_json),
        "created_at": event.created_at.isoformat(),
    }


def transcript_to_dict(transcript: Transcript) -> dict[str, Any]:
    return {
        "id": transcript.id,
        "asset_id": transcript.asset_id,
        "engine": transcript.engine,
        "language": transcript.language,
        "text": transcript.text,
        "segments": json.loads(transcript.segments_json),
        "words": json.loads(transcript.words_json),
        "status": transcript.status,
        "created_at": transcript.created_at.isoformat(),
    }


def schedule_slot_to_dict(slot: ScheduleSlot) -> dict[str, Any]:
    return {
        "id": slot.id,
        "publish_task_id": slot.publish_task_id,
        "platform": slot.platform,
        "publish_at": slot.publish_at.isoformat(),
        "status": slot.status,
        "order_index": slot.order_index,
        "notes": slot.notes,
        "created_at": slot.created_at.isoformat(),
        "updated_at": slot.updated_at.isoformat(),
    }

