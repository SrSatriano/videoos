from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..config import PROXIES_DIR, RENDER_TIMEOUT_SECONDS
from ..models import Asset, AssetProxy, SceneMarker
from .audit import record_event
from .media import FFmpegUnavailable, ensure_ffmpeg, ffprobe_metadata


SCENE_TIME_RE = re.compile(r"pts_time:([0-9]+(?:\.[0-9]+)?)")


EXPORT_PRESETS: list[dict[str, Any]] = [
    {
        "id": "preview_fast",
        "name": "Preview rapido",
        "category": "proxy",
        "description": "H.264 leve para revisar corte, legenda e ritmo sem pesar a maquina.",
        "width": 720,
        "height": 1280,
        "codec": "H.264/AAC",
        "crf": 30,
        "preset": "ultrafast",
        "use_case": "review",
    },
    {
        "id": "shorts_quality",
        "name": "Shorts qualidade",
        "category": "publish",
        "description": "Export principal 9:16 para Reels, TikTok e Shorts com equilibrio entre qualidade e tamanho.",
        "width": 1080,
        "height": 1920,
        "codec": "H.264/AAC",
        "crf": 21,
        "preset": "medium",
        "use_case": "publish",
    },
    {
        "id": "archive_master",
        "name": "Master arquivo",
        "category": "archive",
        "description": "Arquivo local com CRF mais baixo para guardar uma versao final melhor.",
        "width": 1080,
        "height": 1920,
        "codec": "H.264/AAC",
        "crf": 18,
        "preset": "slow",
        "use_case": "archive",
    },
    {
        "id": "light_upload",
        "name": "Upload leve",
        "category": "publish",
        "description": "Versao menor para contas em volume, validacao rapida e conexoes lentas.",
        "width": 720,
        "height": 1280,
        "codec": "H.264/AAC",
        "crf": 25,
        "preset": "veryfast",
        "use_case": "bulk",
    },
]


def export_presets() -> list[dict[str, Any]]:
    return EXPORT_PRESETS


def get_asset_or_404(db: Session, asset_id: str) -> Asset:
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset nao encontrado.")
    return asset


def generate_asset_proxy(db: Session, asset_id: str) -> AssetProxy:
    asset = get_asset_or_404(db, asset_id)
    source = Path(asset.stored_path)
    if not source.exists():
        raise HTTPException(status_code=404, detail="Arquivo original do asset nao encontrado.")

    PROXIES_DIR.mkdir(parents=True, exist_ok=True)
    target = PROXIES_DIR / f"{asset.id}_720p.mp4"
    try:
        ensure_ffmpeg()
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-nostdin",
                "-y",
                "-i",
                str(source),
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
                "-vf",
                "scale=720:-2",
                "-c:v",
                "libx264",
                "-crf",
                "30",
                "-preset",
                "ultrafast",
                "-c:a",
                "aac",
                "-b:a",
                "96k",
                "-movflags",
                "+faststart",
                str(target),
            ],
            capture_output=True,
            check=True,
            text=True,
            encoding="utf-8",
            timeout=RENDER_TIMEOUT_SECONDS,
        )
        metadata = ffprobe_metadata(target)
        proxy = db.query(AssetProxy).filter(AssetProxy.asset_id == asset.id).first()
        if not proxy:
            proxy = AssetProxy(asset_id=asset.id, path=str(target))
            db.add(proxy)
        proxy.path = str(target)
        proxy.width = metadata.get("width")
        proxy.height = metadata.get("height")
        proxy.size_bytes = target.stat().st_size if target.exists() else 0
        proxy.status = "ready"
        proxy.error_message = None
        db.commit()
        db.refresh(proxy)
        record_event(
            db,
            event_type="asset_proxy_generated",
            entity_type="asset",
            entity_id=asset.id,
            message=f"Proxy 720p gerado para {asset.filename}.",
            payload={"proxy_path": str(target)},
        )
        return proxy
    except (FFmpegUnavailable, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        message = "FFmpeg indisponivel." if isinstance(exc, FFmpegUnavailable) else str(exc)
        proxy = db.query(AssetProxy).filter(AssetProxy.asset_id == asset.id).first()
        if not proxy:
            proxy = AssetProxy(asset_id=asset.id, path=str(target))
            db.add(proxy)
        proxy.status = "failed"
        proxy.error_message = message
        db.commit()
        db.refresh(proxy)
        raise HTTPException(status_code=500, detail=f"Falha ao gerar proxy: {message}") from exc


def list_asset_proxies(db: Session, asset_id: str) -> list[AssetProxy]:
    get_asset_or_404(db, asset_id)
    return db.query(AssetProxy).filter(AssetProxy.asset_id == asset_id).order_by(AssetProxy.created_at.desc()).all()


def create_marker(
    db: Session,
    asset_id: str,
    *,
    time_seconds: float,
    duration_seconds: float | None,
    label: str,
    color: str,
    marker_type: str,
    notes: str = "",
    source: str = "manual",
) -> SceneMarker:
    asset = get_asset_or_404(db, asset_id)
    marker = SceneMarker(
        asset_id=asset.id,
        time_seconds=time_seconds,
        duration_seconds=duration_seconds,
        label=label,
        color=color,
        marker_type=marker_type,
        source=source,
        notes=notes,
    )
    db.add(marker)
    db.commit()
    db.refresh(marker)
    record_event(
        db,
        event_type="scene_marker_created",
        entity_type="asset",
        entity_id=asset.id,
        message=f"Marcador criado em {time_seconds:.2f}s para {asset.filename}.",
        payload={"marker_id": marker.id, "source": source, "type": marker_type},
    )
    return marker


def list_markers(db: Session, asset_id: str) -> list[SceneMarker]:
    get_asset_or_404(db, asset_id)
    return (
        db.query(SceneMarker)
        .filter(SceneMarker.asset_id == asset_id)
        .order_by(SceneMarker.time_seconds.asc(), SceneMarker.created_at.asc())
        .all()
    )


def delete_marker(db: Session, marker_id: str) -> None:
    marker = db.get(SceneMarker, marker_id)
    if not marker:
        raise HTTPException(status_code=404, detail="Marcador nao encontrado.")
    db.delete(marker)
    db.commit()


def detect_scene_times(path: Path, threshold: float, limit: int) -> list[float]:
    ensure_ffmpeg()
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostdin",
            "-i",
            str(path),
            "-vf",
            f"select=gt(scene\\,{threshold}),showinfo",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        check=True,
        text=True,
        encoding="utf-8",
        timeout=RENDER_TIMEOUT_SECONDS,
    )
    raw_times = [float(match.group(1)) for match in SCENE_TIME_RE.finditer(result.stderr)]
    deduped: list[float] = []
    for time_seconds in sorted(set(raw_times)):
        if time_seconds < 0.25:
            continue
        if deduped and abs(time_seconds - deduped[-1]) < 0.5:
            continue
        deduped.append(time_seconds)
        if len(deduped) >= limit:
            break
    return deduped


def detect_and_store_scenes(db: Session, asset_id: str, *, threshold: float, limit: int) -> list[SceneMarker]:
    asset = get_asset_or_404(db, asset_id)
    source = Path(asset.stored_path)
    if not source.exists():
        raise HTTPException(status_code=404, detail="Arquivo original do asset nao encontrado.")

    try:
        times = detect_scene_times(source, threshold, limit)
    except (FFmpegUnavailable, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        message = "FFmpeg indisponivel." if isinstance(exc, FFmpegUnavailable) else str(exc)
        raise HTTPException(status_code=500, detail=f"Falha ao detectar cenas: {message}") from exc

    db.query(SceneMarker).filter(SceneMarker.asset_id == asset.id, SceneMarker.source == "auto_scene").delete()
    markers = [
        SceneMarker(
            asset_id=asset.id,
            time_seconds=time_seconds,
            duration_seconds=None,
            label=f"Cena {index:02d}",
            color="#4da3ff",
            marker_type="scene",
            source="auto_scene",
            notes=f"Detectado por threshold {threshold:.2f}.",
        )
        for index, time_seconds in enumerate(times, start=1)
    ]
    db.add_all(markers)
    db.commit()
    for marker in markers:
        db.refresh(marker)
    record_event(
        db,
        event_type="scene_detection_completed",
        entity_type="asset",
        entity_id=asset.id,
        message=f"{len(markers)} cena(s) detectada(s) em {asset.filename}.",
        payload={"threshold": threshold, "limit": limit},
    )
    return markers
