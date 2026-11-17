from __future__ import annotations

import functools
import hashlib
import json
import os
import shutil
import subprocess
import re
from fractions import Fraction
from pathlib import Path, PureWindowsPath
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..config import (
    ASSETS_DIR,
    ALLOW_ANY_IMPORT_PATH,
    FFPROBE_TIMEOUT_SECONDS,
    HOST_DRIVE_MOUNT,
    INCOMING_DIR,
    IMPORT_ROOTS,
    THUMBNAILS_DIR,
    THUMBNAIL_TIMEOUT_SECONDS,
    PROXIES_DIR,
    VIDEO_EXTENSIONS,
)
from ..models import Asset, AssetProxy, BrollCue, ClipCandidate, RenderJob, SceneMarker, Transcript
from .audit import record_event


class FFmpegUnavailable(RuntimeError):
    pass


def ffmpeg_status() -> dict[str, Any]:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    return {
        "ffmpeg": ffmpeg,
        "ffprobe": ffprobe,
        "available": bool(ffmpeg and ffprobe),
        "hardware_encoders": available_hardware_encoders() if bool(ffmpeg and ffprobe) else [],
    }


def ensure_ffmpeg() -> None:
    status = ffmpeg_status()
    if not status["available"]:
        raise FFmpegUnavailable(
            "FFmpeg/FFprobe nao encontrados. Rode via Docker Compose ou instale FFmpeg no PATH."
        )


@functools.lru_cache(maxsize=1)
def available_video_encoders() -> list[str]:
    try:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return ["libx264"]
        completed = subprocess.run(
            ["ffmpeg", "-encoders"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10,
        )
        if completed.returncode == 0:
            encoders = []
            for line in completed.stdout.splitlines():
                line = line.strip()
                if line.startswith("V"):  # V represents video encoder
                    parts = line.split()
                    if len(parts) >= 2:
                        encoders.append(parts[1])
            return encoders
    except Exception:
        pass
    return ["libx264"]


def available_hardware_encoders() -> list[str]:
    all_enc = available_video_encoders()
    hw_candidates = [
        "h264_nvenc",
        "hevc_nvenc",
        "h264_qsv",
        "hevc_qsv",
        "h264_amf",
        "hevc_amf",
        "h264_videotoolbox",
    ]
    return [enc for enc in hw_candidates if enc in all_enc]


_PROBED_ENCODERS: dict[str, bool] = {}


def probe_hardware_encoder_dry_run(encoder: str) -> bool:
    """Valida se o encoder de GPU física realmente inicializa sem crash de driver."""
    if encoder in _PROBED_ENCODERS:
        return _PROBED_ENCODERS[encoder]
    try:
        cmd = [
            "ffmpeg", "-hide_banner", "-nostats", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=64x64:d=0.04",
            "-c:v", encoder,
            "-frames:v", "1",
            "-f", "null", "-",
        ]
        res = subprocess.run(cmd, capture_output=True, timeout=4)
        ok = (res.returncode == 0)
    except Exception:
        ok = False
    _PROBED_ENCODERS[encoder] = ok
    return ok


def resolve_render_codec(preferred: str | None = None) -> tuple[str, str]:
    """Resolves the best video codec with hardware acceleration and CPU fallback."""
    pref = (preferred or "libx264").strip().lower()
    avail = available_video_encoders()

    if pref in {"auto", "auto_gpu", "gpu"}:
        hw = available_hardware_encoders()
        if "h264_nvenc" in hw:
            return "h264_nvenc", "nvenc"
        if "h264_qsv" in hw:
            return "h264_qsv", "qsv"
        if "h264_amf" in hw:
            return "h264_amf", "amf"
        if "h264_videotoolbox" in hw:
            return "h264_videotoolbox", "videotoolbox"
        return "libx264", "cpu"

    if pref in avail:
        accel = "nvenc" if "nvenc" in pref else "qsv" if "qsv" in pref else "amf" if "amf" in pref else "cpu"
        return pref, accel

    return "libx264", "cpu"





def path_is_allowed(path: Path) -> bool:
    if ALLOW_ANY_IMPORT_PATH:
        return True
    resolved = path.resolve()
    for root in IMPORT_ROOTS:
        root_resolved = root.resolve()
        try:
            common = os.path.commonpath([str(resolved), str(root_resolved)])
        except ValueError:
            continue
        if common == str(root_resolved):
            return True
    return False


def resolve_user_path(raw_path: str) -> Path:
    cleaned = raw_path.strip().strip('"')
    if re.match(r"^[A-Za-z]:[\\/]", cleaned):
        if os.name == "nt":
            return Path(cleaned)
        windows_path = PureWindowsPath(cleaned)
        drive = windows_path.drive.rstrip(":").lower()
        converted = HOST_DRIVE_MOUNT / drive / Path(*windows_path.parts[1:])
        if converted.exists() or (HOST_DRIVE_MOUNT / drive).exists():
            return converted
    return Path(cleaned)


def safe_upload_name(filename: str) -> str:
    name = Path(filename).name
    return "".join(ch if ch.isalnum() or ch in {"-", "_", ".", " "} else "-" for ch in name).strip() or "video.mp4"


def discover_video_files(path: Path) -> list[Path]:
    resolved = path.resolve()
    if not path_is_allowed(resolved):
        roots = ", ".join(str(root) for root in IMPORT_ROOTS)
        raise HTTPException(status_code=400, detail=f"Caminho fora das pastas permitidas: {roots}")
    if resolved.is_file():
        return [resolved] if resolved.suffix.lower() in VIDEO_EXTENSIONS else []
    if resolved.is_dir():
        return [
            candidate
            for candidate in resolved.rglob("*")
            if candidate.is_file() and candidate.suffix.lower() in VIDEO_EXTENSIONS
        ]
    raise HTTPException(status_code=404, detail=f"Caminho nao encontrado: {resolved}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_fps(value: str | None) -> float | None:
    if not value or value == "0/0":
        return None
    try:
        return float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        return None


def optional_int(value: Any) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def optional_float(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def ffprobe_metadata(path: Path) -> dict[str, Any]:
    ensure_ffmpeg()
    result = subprocess.run(
        [
            "ffprobe",
            "-hide_banner",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            str(path),
        ],
        capture_output=True,
        check=True,
        text=True,
        encoding="utf-8",
        timeout=FFPROBE_TIMEOUT_SECONDS,
    )
    payload = json.loads(result.stdout)
    video_stream = next(
        (stream for stream in payload.get("streams", []) if stream.get("codec_type") == "video"),
        {},
    )
    audio_stream = next(
        (stream for stream in payload.get("streams", []) if stream.get("codec_type") == "audio"),
        {},
    )
    format_metadata = payload.get("format", {})
    duration = video_stream.get("duration") or format_metadata.get("duration")
    width = video_stream.get("width")
    height = video_stream.get("height")
    rotation = rotation_for(video_stream)
    display_width, display_height = display_dimensions(width, height, rotation)
    format_bit_rate = optional_float(format_metadata.get("bit_rate"))
    return {
        "duration_seconds": optional_float(duration),
        "width": display_width,
        "height": display_height,
        "fps": parse_fps(video_stream.get("avg_frame_rate")),
        "orientation": orientation_for(display_width, display_height),
        "rotation": rotation,
        "video_codec": video_stream.get("codec_name"),
        "audio_codec": audio_stream.get("codec_name"),
        "audio_sample_rate_hz": optional_int(audio_stream.get("sample_rate")),
        "audio_channels": optional_int(audio_stream.get("channels")),
        "has_audio": bool(audio_stream),
        "container_format": format_metadata.get("format_name"),
        "format_bit_rate_kbps": round(format_bit_rate / 1000, 2) if format_bit_rate is not None else None,
    }


def rotation_for(video_stream: dict[str, Any]) -> int:
    candidates: list[Any] = [video_stream.get("tags", {}).get("rotate")]
    candidates.extend(side_data.get("rotation") for side_data in video_stream.get("side_data_list", []))
    for value in candidates:
        if value in (None, ""):
            continue
        try:
            return int(float(value)) % 360
        except (TypeError, ValueError):
            continue
    return 0


def display_dimensions(width: int | None, height: int | None, rotation: int) -> tuple[int | None, int | None]:
    if not width or not height:
        return None, None
    if rotation in {90, 270}:
        return int(height), int(width)
    return int(width), int(height)


def orientation_for(width: int | None, height: int | None) -> str:
    if not width or not height:
        return "unknown"
    if height > width:
        return "vertical"
    if width > height:
        return "horizontal"
    return "square"


def generate_thumbnail(input_path: Path, output_path: Path, at_seconds: float | None = None) -> None:
    ensure_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = str(max(0.0, at_seconds if at_seconds is not None else 2.0))
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostdin",
            "-y",
            "-ss",
            timestamp,
            "-i",
            str(input_path),
            "-frames:v",
            "1",
            "-vf",
            "scale=480:-2",
            str(output_path),
        ],
        capture_output=True,
        check=True,
        text=True,
        encoding="utf-8",
        timeout=THUMBNAIL_TIMEOUT_SECONDS,
    )


def import_file(db: Session, source: Path, *, copy_to_library: bool = True) -> Asset:
    file_hash = sha256_file(source)
    existing = db.query(Asset).filter(Asset.sha256 == file_hash).first()
    if existing:
        record_event(
            db,
            event_type="asset_duplicate_detected",
            entity_type="asset",
            entity_id=existing.id,
            message=f"Duplicado detectado para {source.name}.",
            payload={"source": str(source)},
        )
        return existing

    asset_id = hashlib.sha1(f"{file_hash}:{source.name}".encode("utf-8")).hexdigest()[:32]
    stored_path = ASSETS_DIR / f"{asset_id}{source.suffix.lower()}"
    if copy_to_library:
        stored_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, stored_path)
    else:
        stored_path = source

    metadata: dict[str, Any] = {}
    metadata_status = "ready"
    thumbnail_path: Path | None = None
    try:
        metadata = ffprobe_metadata(stored_path)
        thumbnail_path = THUMBNAILS_DIR / "assets" / f"{asset_id}.jpg"
        at_seconds = min(5.0, (metadata.get("duration_seconds") or 20.0) * 0.1)
        generate_thumbnail(stored_path, thumbnail_path, at_seconds=at_seconds)
    except (FFmpegUnavailable, subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        metadata_status = "ffmpeg_missing" if isinstance(exc, FFmpegUnavailable) else "metadata_failed"

    asset = Asset(
        id=asset_id,
        original_path=str(source),
        stored_path=str(stored_path),
        filename=source.name,
        sha256=file_hash,
        size_bytes=source.stat().st_size,
        duration_seconds=metadata.get("duration_seconds"),
        width=metadata.get("width"),
        height=metadata.get("height"),
        fps=metadata.get("fps"),
        orientation=metadata.get("orientation", "unknown"),
        thumbnail_path=str(thumbnail_path) if thumbnail_path and thumbnail_path.exists() else None,
        metadata_status=metadata_status,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    record_event(
        db,
        event_type="asset_imported",
        entity_type="asset",
        entity_id=asset.id,
        message=f"Video importado: {asset.filename}.",
        payload={"metadata_status": metadata_status, "source": str(source)},
    )
    return asset


def import_paths(db: Session, paths: list[str], *, copy_to_library: bool = True) -> list[Asset]:
    imported: list[Asset] = []
    for raw_path in paths:
        for file_path in discover_video_files(resolve_user_path(raw_path)):
            imported.append(import_file(db, file_path, copy_to_library=copy_to_library))
    return imported


def delete_assets(db: Session, asset_ids: list[str]) -> dict[str, Any]:
    """Remove assets da biblioteca (somente registros no banco; o arquivo permanece no disco).

    Assets ja usados em lotes/renders sao bloqueados e retornados em `skipped`, para nao
    quebrar trabalho ja renderizado."""
    deleted: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    missing: list[str] = []

    for asset_id in asset_ids:
        asset = db.get(Asset, asset_id)
        if asset is None:
            missing.append(asset_id)
            continue
        job_count = db.query(RenderJob).filter(RenderJob.asset_id == asset_id).count()
        if job_count:
            skipped.append(
                {
                    "id": asset_id,
                    "filename": asset.filename,
                    "reason": f"em uso em {job_count} render/lote(s)",
                }
            )
            continue

        filename = asset.filename
        db.query(BrollCue).filter(BrollCue.asset_id == asset_id).delete(synchronize_session=False)
        db.query(ClipCandidate).filter(ClipCandidate.asset_id == asset_id).delete(synchronize_session=False)
        # Clean up physical proxy files
        proxies = db.query(AssetProxy).filter(AssetProxy.asset_id == asset_id).all()
        for p in proxies:
            try:
                p_path = Path(p.path)
                if p_path.exists() and p_path.is_file():
                    p_path.unlink()
            except Exception:
                pass
        db.query(AssetProxy).filter(AssetProxy.asset_id == asset_id).delete(synchronize_session=False)
        db.query(SceneMarker).filter(SceneMarker.asset_id == asset_id).delete(synchronize_session=False)
        if asset.thumbnail_path:
            try:
                thumb_p = Path(asset.thumbnail_path)
                if thumb_p.exists() and thumb_p.is_file():
                    thumb_p.unlink()
            except Exception:
                pass

        # If asset was copied into internal ASSETS_DIR, remove the copy (never touch external original_path)
        try:
            stored_p = Path(asset.stored_path).resolve()
            assets_root = ASSETS_DIR.resolve()
            if assets_root in stored_p.parents and stored_p.is_file():
                stored_p.unlink()
        except Exception:
            pass

        db.delete(asset)
        deleted.append({"id": asset_id, "filename": filename})

    if deleted:
        db.commit()
        record_event(
            db,
            event_type="assets_deleted",
            entity_type="asset",
            entity_id=deleted[0]["id"],
            message=f"{len(deleted)} video(s) removido(s) da biblioteca.",
            payload={
                "deleted": [item["id"] for item in deleted],
                "skipped": [item["id"] for item in skipped],
            },
        )

    return {
        "deleted": deleted,
        "skipped": skipped,
        "missing": missing,
        "deleted_count": len(deleted),
        "skipped_count": len(skipped),
    }


def existing_asset_path(asset: Asset) -> Path | None:
    stored_path = Path(asset.stored_path)
    if stored_path.exists():
        return stored_path

    for candidate in sorted(ASSETS_DIR.glob(f"{asset.id}.*")):
        if candidate.is_file() and candidate.suffix.lower() in VIDEO_EXTENSIONS:
            return candidate

    filename_candidate = ASSETS_DIR / Path(asset.filename).name
    if filename_candidate.exists() and filename_candidate.suffix.lower() in VIDEO_EXTENSIONS:
        return filename_candidate

    original_path = Path(asset.original_path)
    if original_path.exists() and original_path.suffix.lower() in VIDEO_EXTENSIONS:
        return original_path

    return None


def reindex_asset(db: Session, asset: Asset, *, force_thumbnail: bool = False) -> dict[str, Any]:
    source = existing_asset_path(asset)
    if not source:
        asset.metadata_status = "file_missing"
        db.commit()
        record_event(
            db,
            event_type="asset_reindex_failed",
            entity_type="asset",
            entity_id=asset.id,
            message=f"Arquivo fisico nao encontrado para {asset.filename}.",
            payload={"stored_path": asset.stored_path},
        )
        return {"id": asset.id, "filename": asset.filename, "status": "file_missing", "repaired": False}

    metadata: dict[str, Any] = {}
    thumbnail_path = Path(asset.thumbnail_path) if asset.thumbnail_path else THUMBNAILS_DIR / "assets" / f"{asset.id}.jpg"
    metadata_status = "ready"
    error_message = ""
    try:
        metadata = ffprobe_metadata(source)
        if force_thumbnail or not thumbnail_path.exists():
            at_seconds = min(5.0, (metadata.get("duration_seconds") or 20.0) * 0.1)
            generate_thumbnail(source, thumbnail_path, at_seconds=at_seconds)
    except FFmpegUnavailable as exc:
        metadata_status = "ffmpeg_missing"
        error_message = str(exc)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        metadata_status = "metadata_failed"
        error_message = str(exc)

    asset.stored_path = str(source)
    asset.size_bytes = source.stat().st_size
    asset.duration_seconds = metadata.get("duration_seconds")
    asset.width = metadata.get("width")
    asset.height = metadata.get("height")
    asset.fps = metadata.get("fps")
    asset.orientation = metadata.get("orientation", "unknown")
    asset.thumbnail_path = str(thumbnail_path) if thumbnail_path.exists() else None
    if metadata_status == "ready" and not asset.thumbnail_path:
        metadata_status = "thumbnail_missing"
    asset.metadata_status = metadata_status
    db.commit()
    db.refresh(asset)

    event_type = "asset_reindexed" if metadata_status == "ready" else "asset_reindex_failed"
    record_event(
        db,
        event_type=event_type,
        entity_type="asset",
        entity_id=asset.id,
        message=f"Reindexacao do asset {asset.filename}: {metadata_status}.",
        payload={
            "stored_path": asset.stored_path,
            "metadata_status": metadata_status,
            "error": error_message,
        },
    )
    return {
        "id": asset.id,
        "filename": asset.filename,
        "status": metadata_status,
        "repaired": metadata_status == "ready",
    }


def reindex_assets(
    db: Session,
    *,
    asset_id: str | None = None,
    only_attention: bool = True,
    force_thumbnail: bool = False,
) -> dict[str, Any]:
    query = db.query(Asset).order_by(Asset.created_at.desc())
    if asset_id:
        query = query.filter(Asset.id == asset_id)
    assets = query.all()
    results: list[dict[str, Any]] = []
    skipped = 0

    for asset in assets:
        needs_attention = asset.metadata_status != "ready" or not asset.thumbnail_path or not existing_asset_path(asset)
        if only_attention and not needs_attention:
            skipped += 1
            continue
        results.append(reindex_asset(db, asset, force_thumbnail=force_thumbnail))

    return {
        "checked": len(results),
        "repaired": sum(1 for item in results if item["repaired"]),
        "failed": sum(1 for item in results if not item["repaired"]),
        "skipped": skipped,
        "results": results,
    }


def save_upload(filename: str, content: bytes) -> Path:
    target_dir = INCOMING_DIR / "explorer"
    target_dir.mkdir(parents=True, exist_ok=True)
    base = safe_upload_name(filename)
    target = target_dir / base
    counter = 1
    while target.exists():
        target = target_dir / f"{target.stem}-{counter}{target.suffix}"
        counter += 1
    target.write_bytes(content)
    return target
