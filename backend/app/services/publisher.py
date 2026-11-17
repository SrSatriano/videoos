import json
import subprocess
from datetime import datetime
from pathlib import Path


from sqlalchemy.orm import Session

from ..config import PUBLISH_PACKAGES_DIR
from ..models import PlatformPreset, PublishTask, RenderedVideo, Transcript, ScheduleSlot
from .audit import record_event
from .captions import build_srt, build_vtt, clean_transcript_segments
from .media import ensure_ffmpeg, sha256_file
from .path_policy import resolve_allowed_directory
from .quality import audio_quality_issues, render_metadata



def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value).strip("-")


def _dimension_label(width: int | None, height: int | None) -> str:
    if width is None or height is None:
        return "unknown"
    return f"{width}x{height}"


def build_quality_report(
    *,
    rendered: RenderedVideo,
    preset: PlatformPreset,
    checklist: list[str],
    thumbnail_present: bool,
    technical_metadata: dict,
) -> dict:
    audio_issues = audio_quality_issues(technical_metadata)
    audio_errors = [item for item in audio_issues if item["severity"] == "error"]
    checks = [
        {
            "id": "render_approved",
            "label": "Render aprovado",
            "expected": "approved",
            "actual": rendered.status,
            "passed": rendered.status == "approved",
        },
        {
            "id": "resolution_matches_platform",
            "label": "Resolucao conforme preset",
            "expected": _dimension_label(preset.width, preset.height),
            "actual": _dimension_label(rendered.width, rendered.height),
            "passed": rendered.width == preset.width and rendered.height == preset.height,
        },
        {
            "id": "duration_available",
            "label": "Duracao registrada",
            "expected": "duration_seconds > 0",
            "actual": rendered.duration_seconds,
            "passed": bool(rendered.duration_seconds and rendered.duration_seconds > 0),
        },
        {
            "id": "thumbnail_present",
            "label": "Thumbnail no pacote",
            "expected": True,
            "actual": thumbnail_present,
            "passed": thumbnail_present,
        },
        {
            "id": "manual_checklist_present",
            "label": "Checklist manual presente",
            "expected": "at least 1 item",
            "actual": len(checklist),
            "passed": len(checklist) > 0,
        },
        {
            "id": "audio_signal_valid",
            "label": "Sinal de audio sem silencio ou clipping",
            "expected": "no silence or clipping",
            "actual": technical_metadata.get("loudness", {"status": "unavailable"}),
            "passed": not audio_errors,
        },
    ]
    passed_count = sum(1 for check in checks if check["passed"])
    score = round((passed_count / len(checks)) * 100, 2) if checks else 0.0
    return {
        "schema_version": "videoos-quality-report/v2",
        "rendered_video_id": rendered.id,
        "platform": preset.platform,
        "platform_label": preset.label,
        "source": "ffprobe_loudnorm_and_render_metadata",
        "actual": {
            "width": technical_metadata.get("width"),
            "height": technical_metadata.get("height"),
            "duration_seconds": technical_metadata.get("duration_seconds"),
            "status": rendered.status,
            "file_size_bytes": technical_metadata.get("size_bytes"),
            "render_seconds": technical_metadata.get("render_seconds"),
            "peak_rss_bytes": technical_metadata.get("peak_rss_bytes"),
            "fps": technical_metadata.get("fps"),
            "bitrate_kbps": technical_metadata.get("bitrate_kbps"),
            "video_codec": technical_metadata.get("video_codec"),
            "audio_codec": technical_metadata.get("audio_codec"),
            "audio_sample_rate_hz": technical_metadata.get("audio_sample_rate_hz"),
            "audio_channels": technical_metadata.get("audio_channels"),
            "has_audio": technical_metadata.get("has_audio"),
            "container_format": technical_metadata.get("container_format"),
            "loudness": technical_metadata.get("loudness", {"status": "unavailable"}),
        },
        "expected": {
            "width": preset.width,
            "height": preset.height,
            "codec": preset.codec,
            "manual_publication": True,
        },
        "checks": checks,
        "audio_issues": audio_issues,
        "passed": passed_count == len(checks),
        "score": score,
        "safe_zone_guide": {
            "enabled": True,
            "note": "Revisar sobreposicoes e area segura antes da publicacao manual.",
        },
    }


def generate_package(
    db: Session,
    *,
    rendered: RenderedVideo,
    platform: str,
    caption: str,
    hashtags: list[str],
    output_dir: str | None = None,
    technical_metadata: dict | None = None,
) -> PublishTask:
    preset = db.query(PlatformPreset).filter(PlatformPreset.platform == platform).first()
    if not preset:
        raise ValueError(f"Preset de plataforma nao encontrado: {platform}")
    base_dir = resolve_allowed_directory(output_dir, field_name="output_dir") if output_dir else PUBLISH_PACKAGES_DIR
    package_dir = base_dir / safe_name(platform) / rendered.id
    package_dir.mkdir(parents=True, exist_ok=True)

    video_target = package_dir / "video.mp4"
    from .media import ffmpeg_status
    if ffmpeg_status().get("available"):
        try:
            subprocess.run(
                [
                    "ffmpeg", "-hide_banner", "-nostdin", "-y",
                    "-i", str(rendered.path),
                    "-c", "copy",
                    "-movflags", "+faststart",
                    str(video_target),
                ],
                capture_output=True,
                timeout=60,
            )
        except Exception:
            pass
    if not video_target.exists() or video_target.stat().st_size == 0:
        import shutil
        shutil.copy2(rendered.path, video_target)


    if rendered.thumbnail_path and Path(rendered.thumbnail_path).exists():
        import shutil
        shutil.copy2(rendered.thumbnail_path, package_dir / "thumbnail.jpg")
    thumbnail_present = (package_dir / "thumbnail.jpg").exists()

    # Exportar Legendas SRT e VTT limpas caso haja transcrição
    srt_present = False
    vtt_present = False
    transcript = db.query(Transcript).filter(Transcript.asset_id == rendered.asset_id).first()
    if transcript and transcript.segments_json:
        try:
            raw_segments = json.loads(transcript.segments_json)
            clean_segs = clean_transcript_segments(raw_segments)
            (package_dir / "subtitles.srt").write_text(build_srt(clean_segs), encoding="utf-8")
            (package_dir / "subtitles.vtt").write_text(build_vtt(clean_segs), encoding="utf-8")
            srt_present = True
            vtt_present = True
        except Exception:
            pass

    normalized_hashtags = [tag if tag.startswith("#") else f"#{tag}" for tag in hashtags]
    checklist = json.loads(preset.checklist_json)
    technical_metadata = technical_metadata or render_metadata(rendered)
    quality_report = build_quality_report(
        rendered=rendered,
        preset=preset,
        checklist=checklist,
        thumbnail_present=thumbnail_present,
        technical_metadata=technical_metadata,
    )
    metadata = {
        "schema_version": "videoos-publish-manifest/v2",
        "rendered_video_id": rendered.id,
        "platform": platform,
        "platform_label": preset.label,
        "video": "video.mp4",
        "video_sha256": sha256_file(video_target),
        "thumbnail": "thumbnail.jpg" if thumbnail_present else None,
        "subtitles_srt": "subtitles.srt" if srt_present else None,
        "subtitles_vtt": "subtitles.vtt" if vtt_present else None,
        "quality_report": "quality-report.json",
        "caption": caption,
        "hashtags": normalized_hashtags,
        "width": preset.width,
        "height": preset.height,
        "codec": preset.codec,
        "manual_publication": True,
    }
    (package_dir / "caption.txt").write_text(caption.strip() + "\n", encoding="utf-8")
    (package_dir / "hashtags.txt").write_text(" ".join(normalized_hashtags) + "\n", encoding="utf-8")
    (package_dir / "copy.txt").write_text(
        f"{caption.strip()}\n.\n.\n{' '.join(normalized_hashtags)}\n",
        encoding="utf-8",
    )
    (package_dir / "checklist.md").write_text(
        "\n".join(f"- [ ] {item}" for item in checklist) + "\n",
        encoding="utf-8",
    )
    (package_dir / "quality-report.json").write_text(
        json.dumps(quality_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (package_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


    task = PublishTask(
        rendered_video_id=rendered.id,
        platform=platform,
        status="ready",
        package_dir=str(package_dir),
        caption=caption,
        hashtags_json=json.dumps(normalized_hashtags, ensure_ascii=False),
        checklist_json=json.dumps(checklist, ensure_ascii=False),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    record_event(
        db,
        event_type="publish_package_created",
        entity_type="publish_task",
        entity_id=task.id,
        message=f"Pacote gerado para {preset.label}.",
        payload={"package_dir": str(package_dir)},
    )
    return task
