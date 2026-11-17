from __future__ import annotations

import json
import math
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..config import FFPROBE_TIMEOUT_SECONDS
from ..models import RenderedVideo, Asset
from .media import ensure_ffmpeg, ffprobe_metadata, sha256_file
from .audit import record_event


PLATFORM_LABELS = {
    "instagram_reels": "Instagram Reels",
    "tiktok": "TikTok",
    "youtube_shorts": "YouTube Shorts",
}

SAFE_ZONE_GUIDES = {
    "instagram_reels": {
        "platform": "instagram_reels",
        "label": "Instagram Reels",
        "top_pct": 14,
        "right_pct": 10,
        "bottom_pct": 22,
        "left_pct": 6,
        "notes": [
            "Zona conservadora para manter gancho, CTA, legenda e marca fora da interface do Reels.",
            "Priorize audio, vertical 9:16 e mensagens principais dentro do centro.",
        ],
    },
    "tiktok": {
        "platform": "tiktok",
        "label": "TikTok",
        "top_pct": 12,
        "right_pct": 18,
        "bottom_pct": 24,
        "left_pct": 6,
        "notes": [
            "Zona conservadora com folga maior na direita e no rodape por causa dos botoes e legenda.",
            "Use 9:16 e deixe CTA fora do canto inferior direito.",
        ],
    },
    "youtube_shorts": {
        "platform": "youtube_shorts",
        "label": "YouTube Shorts",
        "top_pct": 10,
        "right_pct": 12,
        "bottom_pct": 20,
        "left_pct": 6,
        "notes": [
            "Zona conservadora para evitar sobreposicao com titulo, botoes e controles do Shorts.",
            "Videos verticais ou quadrados ate 3 minutos podem ser classificados como Shorts.",
        ],
    },
}

QUALITY_CACHE_SCHEMA = "videoos-qc-cache/v1"


def universal_safe_zone(platforms: list[str]) -> dict[str, Any]:
    guides = [SAFE_ZONE_GUIDES[platform] for platform in platforms if platform in SAFE_ZONE_GUIDES]
    if not guides:
        guides = list(SAFE_ZONE_GUIDES.values())

    return {
        "platform": "universal",
        "label": "Universal",
        "top_pct": max(guide["top_pct"] for guide in guides),
        "right_pct": max(guide["right_pct"] for guide in guides),
        "bottom_pct": max(guide["bottom_pct"] for guide in guides),
        "left_pct": max(guide["left_pct"] for guide in guides),
        "notes": ["Zona mais conservadora combinando as plataformas selecionadas."],
    }


def _loudness_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return round(number, 2) if math.isfinite(number) else None


def measure_audio_loudness(path: Path) -> dict[str, Any]:
    targets = {
        "target_integrated_lufs": -14.0,
        "target_true_peak_dbtp": -1.5,
        "target_lra_lu": 11.0,
    }
    try:
        ensure_ffmpeg()
        completed = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-nostdin",
                "-i",
                str(path),
                "-map",
                "0:a:0",
                "-af",
                "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=FFPROBE_TIMEOUT_SECONDS,
        )
        output = completed.stderr or ""
        candidates = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", output, flags=re.DOTALL)
        if completed.returncode != 0 or not candidates:
            return {"status": "unavailable", **targets}
        payload = json.loads(candidates[-1])
        integrated_raw = str(payload.get("input_i", "")).strip().lower()
        status = "silent" if integrated_raw in {"-inf", "-infinity"} else "measured"
        return {
            "status": status,
            "integrated_lufs": _loudness_number(payload.get("input_i")),
            "true_peak_dbtp": _loudness_number(payload.get("input_tp")),
            "loudness_range_lu": _loudness_number(payload.get("input_lra")),
            "threshold_lufs": _loudness_number(payload.get("input_thresh")),
            **targets,
        }
    except Exception:
        return {"status": "unavailable", **targets}


def render_metadata(rendered: RenderedVideo, *, measure_loudness: bool = True) -> dict[str, Any]:
    path = Path(rendered.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Arquivo renderizado nao encontrado.")

    metadata: dict[str, Any] = {
        "width": rendered.width,
        "height": rendered.height,
        "duration_seconds": rendered.duration_seconds,
        "fps": None,
        "size_bytes": path.stat().st_size,
        "render_seconds": rendered.render_seconds,
        "peak_rss_bytes": rendered.peak_rss_bytes,
        "path": str(path),
    }
    try:
        probed = ffprobe_metadata(path)
        metadata.update({key: value for key, value in probed.items() if value is not None})
    except Exception:
        # The stored render metadata is still enough for most checks.
        pass

    width = metadata.get("width") or 0
    height = metadata.get("height") or 0
    duration = metadata.get("duration_seconds") or 0
    metadata["aspect_ratio"] = round(width / height, 4) if width and height else None
    metadata["orientation"] = "vertical" if height > width else "square" if height == width and width else "horizontal"
    metadata["bitrate_kbps"] = metadata.get("format_bit_rate_kbps")
    if metadata["bitrate_kbps"] is None and duration:
        metadata["bitrate_kbps"] = round((metadata["size_bytes"] * 8) / duration / 1000, 2)
    if measure_loudness:
        if metadata.get("has_audio") is True:
            metadata["loudness"] = measure_audio_loudness(path)
        elif metadata.get("has_audio") is False:
            metadata["loudness"] = {"status": "no_audio"}
        else:
            metadata["loudness"] = {"status": "unavailable"}
    return metadata


def analyze_render(db: Session, rendered: RenderedVideo) -> tuple[dict[str, Any], dict[str, Any]]:
    path = Path(rendered.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Arquivo renderizado nao encontrado.")

    file_sha256 = sha256_file(path)
    try:
        cached = json.loads(rendered.quality_cache_json) if rendered.quality_cache_json else {}
    except (TypeError, json.JSONDecodeError):
        cached = {}
    cached_metadata = cached.get("metadata")
    if (
        cached.get("schema_version") == QUALITY_CACHE_SCHEMA
        and cached.get("file_sha256") == file_sha256
        and isinstance(cached_metadata, dict)
    ):
        return cached_metadata, {
            "status": "hit",
            "schema_version": QUALITY_CACHE_SCHEMA,
            "file_sha256": file_sha256,
            "analyzed_at": cached.get("analyzed_at"),
        }

    metadata = render_metadata(rendered)
    analyzed_at = datetime.now(UTC).replace(tzinfo=None).isoformat()
    rendered.quality_cache_json = json.dumps(
        {
            "schema_version": QUALITY_CACHE_SCHEMA,
            "file_sha256": file_sha256,
            "file_size_bytes": path.stat().st_size,
            "analyzed_at": analyzed_at,
            "metadata": metadata,
        },
        ensure_ascii=False,
    )
    db.commit()
    return metadata, {
        "status": "miss",
        "schema_version": QUALITY_CACHE_SCHEMA,
        "file_sha256": file_sha256,
        "analyzed_at": analyzed_at,
    }


def issue(severity: str, message: str, fix: str = "", code: str | None = None) -> dict[str, str]:
    result = {"severity": severity, "message": message, "fix": fix}
    if code:
        result["code"] = code
    return result


def audio_quality_issues(metadata: dict[str, Any]) -> list[dict[str, str]]:
    loudness = metadata.get("loudness") or {}
    status = loudness.get("status")
    if status == "silent":
        return [
            issue(
                "error",
                "A faixa de audio esta silenciosa.",
                "Revise o audio original ou aplique uma musica antes de exportar.",
                "audio_silence",
            )
        ]
    if status == "no_audio":
        return [
            issue(
                "warning",
                "O arquivo nao possui faixa de audio.",
                "Confirme se o video deve ser mudo ou adicione uma trilha licenciada.",
                "audio_missing",
            )
        ]
    if status != "measured":
        return [
            issue(
                "info",
                "A analise de audio nao ficou disponivel.",
                "Execute o QC novamente com FFmpeg disponivel.",
                "audio_unavailable",
            )
        ]

    issues: list[dict[str, str]] = []
    true_peak = loudness.get("true_peak_dbtp")
    integrated = loudness.get("integrated_lufs")
    if true_peak is not None and true_peak >= 0:
        issues.append(
            issue(
                "error",
                "O audio apresenta risco de clipping no true peak.",
                "Reduza o ganho ou normalize com limite de true peak abaixo de -1 dBTP.",
                "audio_clipping",
            )
        )
    elif true_peak is not None and true_peak > -1:
        issues.append(
            issue(
                "warning",
                "O audio tem pouca margem antes do clipping.",
                "Reduza o ganho para manter o true peak em -1 dBTP ou menos.",
                "audio_low_headroom",
            )
        )
    if integrated is not None and integrated < -24:
        issues.append(
            issue(
                "warning",
                "O audio esta muito baixo para consumo em dispositivos moveis.",
                "Normalize o loudness e confira novamente antes da publicacao.",
                "audio_too_quiet",
            )
        )
    elif integrated is not None and integrated > -10:
        issues.append(
            issue(
                "warning",
                "O audio esta acima da faixa operacional recomendada.",
                "Reduza o ganho e preserve margem de true peak.",
                "audio_too_loud",
            )
        )
    return issues


def score_for(issues: list[dict[str, str]]) -> int:
    score = 100
    for item in issues:
        if item["severity"] == "error":
            score -= 25
        elif item["severity"] == "warning":
            score -= 10
    return max(score, 0)


def check_instagram(metadata: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    width = metadata.get("width") or 0
    height = metadata.get("height") or 0
    ratio = metadata.get("aspect_ratio")
    fps = metadata.get("fps")
    duration = metadata.get("duration_seconds") or 0
    if not width or not height:
        issues.append(issue("error", "Resolucao ausente.", "Reprocesse o render para registrar width/height."))
    elif min(width, height) < 720:
        issues.append(issue("error", "Instagram Reels exige resolucao minima de 720px.", "Exporte em 1080x1920."))
    if ratio is None or ratio < 0.54 or ratio > 1.92:
        issues.append(issue("error", "Aspect ratio fora do intervalo aceito pelo Reels.", "Use 9:16 para shorts verticais."))
    if fps is None:
        issues.append(issue("info", "Taxa de quadros nao detectada nos metadados. Assegure que o video final tenha 30 FPS ou mais.", "Verifique as configuracoes do seu template."))
    elif fps < 23:
        issues.append(issue("error", "Instagram Reels pede pelo menos 23 FPS.", "Exporte em 30 FPS ou mais."))
    elif fps < 29.5:
        issues.append(issue("info", f"Taxa de quadros de {fps:.1f} FPS e aceita pelo Instagram Reels, mas 30 FPS e recomendado.", "Considere exportar em 30 FPS."))
    if duration > 900:
        issues.append(issue("error", "Instagram Reels aceita no maximo 15 minutos.", "Reduza a duracao do video."))
    elif duration > 90:
        issues.append(issue("warning", "Reels acima de 90 segundos perdem retencao em formatos curtos.", "Considere manter ate 90s para shorts."))
    if ratio is not None and abs(ratio - 0.5625) > 0.03:
        issues.append(issue("warning", "O arquivo passa no intervalo, mas nao esta em 9:16 ideal.", "Use 1080x1920."))
    issues.append(issue("info", "Confira capa 420x654 e texto dentro da area segura.", "Evite CTA encostado nas bordas."))
    return issues


def check_tiktok(metadata: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    width = metadata.get("width") or 0
    height = metadata.get("height") or 0
    ratio = metadata.get("aspect_ratio")
    size_bytes = metadata.get("size_bytes") or 0
    bitrate = metadata.get("bitrate_kbps")
    duration = metadata.get("duration_seconds") or 0
    fps = metadata.get("fps")
    if width < 540 or height < 960:
        issues.append(issue("error", "TikTok recomenda vertical com minimo de 540x960.", "Exporte em 1080x1920."))
    if ratio is None or abs(ratio - 0.5625) > 0.03:
        issues.append(issue("warning", "TikTok aceita outros formatos, mas 9:16 e o recomendado.", "Use 1080x1920."))
    if duration < 3.0:
        issues.append(issue("error", "TikTok exige duracao minima de 3 segundos.", "Use um video de pelo menos 3s."))
    elif duration > 600:
        issues.append(issue("error", "TikTok aceita videos de no maximo 10 minutos.", "Corte ou divida o video."))
    elif duration > 180:
        issues.append(issue("warning", "Videos acima de 3 minutos costumam ter menor distribuicao no TikTok.", "Considere focar em ate 60s ou 3m."))
    if fps is not None and fps < 23:
        issues.append(issue("error", "TikTok pede pelo menos 23 FPS para reproducao fluida.", "Exporte em 30 FPS."))
    if size_bytes > 500 * 1024 * 1024:
        issues.append(issue("error", "Arquivo acima de 500 MB.", "Aumente CRF ou use preset de upload leve."))
    if bitrate is not None and bitrate < 516:
        issues.append(issue("warning", "Bitrate abaixo de 516 kbps.", "Reduza CRF ou revise compressao."))
    issues.append(issue("info", "Mantenha texto importante fora da lateral direita e do rodape.", "Use safe area no template."))
    return issues


def check_youtube(metadata: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    width = metadata.get("width") or 0
    height = metadata.get("height") or 0
    orientation = metadata.get("orientation")
    duration = metadata.get("duration_seconds") or 0
    if orientation not in {"vertical", "square"}:
        issues.append(issue("error", "Shorts precisam ser verticais ou quadrados.", "Exporte em 9:16 ou 1:1."))
    if width and height and min(width, height) < 720:
        issues.append(issue("warning", "YouTube Shorts recomenda resolucao minima de 720p.", "Exporte em 1080x1920."))
    if duration < 1.0:
        issues.append(issue("error", "YouTube Shorts exige duracao minima de 1 segundo.", "Use um video de pelo menos 1s."))
    elif duration > 180:
        issues.append(issue("error", "YouTube Shorts aceita ate 3 minutos.", "Corte ou divida o video."))
    elif duration > 60:
        issues.append(issue("warning", "Short acima de 1 minuto exige cuidado extra com musica/Content ID.", "Use trilha licenciada ou propria."))
    issues.append(issue("info", "Inclua titulo/descricao pensados para Shorts.", "Considere hashtag e gancho nos primeiros segundos."))
    return issues


CHECKERS = {
    "instagram_reels": check_instagram,
    "tiktok": check_tiktok,
    "youtube_shorts": check_youtube,
}


def quality_check_render(db: Session, rendered_id: str, platforms: list[str]) -> dict[str, Any]:
    rendered = db.get(RenderedVideo, rendered_id)
    if not rendered:
        raise HTTPException(status_code=404, detail="Render nao encontrado.")

    metadata, analysis_cache = analyze_render(db, rendered)
    audio_issues = audio_quality_issues(metadata)
    reports = []
    for platform in platforms:
        checker = CHECKERS[platform]
        issues = [*checker(metadata), *audio_issues]
        errors = [item for item in issues if item["severity"] == "error"]
        reports.append(
            {
                "platform": platform,
                "label": PLATFORM_LABELS[platform],
                "passed": not errors,
                "score": score_for(issues),
                "issues": issues,
                "safe_zone": SAFE_ZONE_GUIDES[platform],
            }
        )

    return {
        "rendered_video_id": rendered.id,
        "review_status": rendered.status,
        "package_ready": rendered.status == "approved" and all(report["passed"] for report in reports),
        "analysis_cache": analysis_cache,
        "audio_issues": audio_issues,
        "metadata": metadata,
        "reports": reports,
        "safe_zone_guide": universal_safe_zone(platforms),
    }


def verify_media_integrity(path_str: str) -> dict[str, Any]:
    path = Path(path_str)
    if not path.exists():
        return {
            "valid": False,
            "error_type": "file_missing",
            "message": f"Arquivo fisico ausente no caminho especificado: {path.name}",
            "fix": "Certifique-se de que o arquivo nao foi movido ou deletado manualmente do disco local."
        }
    
    try:
        probed = ffprobe_metadata(path)
        has_video = probed.get("width") is not None and probed.get("height") is not None
    except Exception:
        return {
            "valid": False,
            "error_type": "metadata_corrupt",
            "message": "Metadados de video corrompidos ou ilegiveis pelo FFprobe.",
            "fix": "O arquivo pode nao ser um video valido ou esta severamente corrompido."
        }
        
    if not has_video:
        return {
            "valid": False,
            "error_type": "no_video_stream",
            "message": "O arquivo nao possui uma trilha de video (stream de video) valida.",
            "fix": "Certifique-se de que o arquivo importado de fato contem video."
        }

    try:
        completed = subprocess.run(
            [
                "ffmpeg",
                "-v", "error",
                "-i", str(path),
                "-map", "0:v:0",
                "-frames:v", "5",
                "-f", "null",
                "-"
            ],
            capture_output=True,
            timeout=8
        )
        if completed.returncode != 0:
            err_msg = completed.stderr.decode("utf-8", errors="ignore")[-200:]
            return {
                "valid": False,
                "error_type": "decode_failed",
                "message": f"Falha na decodificacao de frames de teste do video: {err_msg}",
                "fix": "O codec ou streams de frames do arquivo podem estar corrompidos."
            }
    except Exception:
        return {
            "valid": False,
            "error_type": "check_timeout_or_failed",
            "message": "A verificacao de integridade excedeu o tempo limite ou falhou no subprocesso.",
            "fix": "Revise as permissoes de execucao do FFmpeg e a integridade da maquina."
        }

    return {
        "valid": True,
        "error_type": None,
        "message": "Integridade fisica e estrutural do video validada com sucesso.",
        "details": {
            "size_bytes": path.stat().st_size,
            "width": probed.get("width"),
            "height": probed.get("height"),
            "duration": probed.get("duration_seconds")
        }
    }


def check_asset_integrity(db: Session, asset_id: str) -> dict[str, Any]:
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset nao encontrado.")
    
    result = verify_media_integrity(asset.stored_path)
    record_event(
        db,
        event_type="asset_integrity_checked",
        entity_type="asset",
        entity_id=asset.id,
        message=f"Integridade do asset {asset.filename}: {'Valido' if result['valid'] else 'Corrompido/Ausente'}.",
        payload=result
    )
    return result


def check_render_integrity(db: Session, rendered_id: str) -> dict[str, Any]:
    rendered = db.get(RenderedVideo, rendered_id)
    if not rendered:
        raise HTTPException(status_code=404, detail="Render nao encontrado.")
        
    result = verify_media_integrity(rendered.path)
    record_event(
        db,
        event_type="render_integrity_checked",
        entity_type="rendered_video",
        entity_id=rendered.id,
        message=f"Integridade do render {Path(rendered.path).name}: {'Valido' if result['valid'] else 'Corrompido/Ausente'}.",
        payload=result
    )
    return result


def quality_check_batch(
    db: Session,
    batch_id: str,
    platforms: list[str] | None = None,
) -> dict[str, Any]:
    from ..models import Batch
    batch = db.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Lote nao encontrado.")

    target_platforms = platforms or ["instagram_reels", "tiktok", "youtube_shorts"]
    
    rendered_videos: list[RenderedVideo] = []
    for job in batch.jobs:
        if job.rendered_video:
            rendered_videos.append(job.rendered_video)

    results: list[dict[str, Any]] = []
    passed_count = 0
    warning_count = 0
    error_count = 0
    total_score = 0

    for rendered in rendered_videos:
        qc_result = quality_check_render(db, rendered.id, target_platforms)
        has_error = not all(report["passed"] for report in qc_result["reports"])
        has_warning = any(
            any(issue["severity"] == "warning" for issue in report["issues"])
            for report in qc_result["reports"]
        )
        avg_score = round(sum(report["score"] for report in qc_result["reports"]) / len(qc_result["reports"])) if qc_result["reports"] else 0
        total_score += avg_score

        if has_error:
            error_count += 1
        else:
            passed_count += 1
        if has_warning:
            warning_count += 1

        results.append({
            "rendered_video_id": rendered.id,
            "filename": Path(rendered.path).name,
            "status": rendered.status,
            "passed": not has_error,
            "score": avg_score,
            "audio_issues": qc_result["audio_issues"],
            "reports": qc_result["reports"],
        })

    total_renders = len(rendered_videos)
    avg_batch_score = round(total_score / total_renders) if total_renders > 0 else 0
    pass_rate = round((passed_count / total_renders) * 100, 1) if total_renders > 0 else 0.0

    summary = {
        "batch_id": batch.id,
        "batch_name": batch.name,
        "total_renders": total_renders,
        "passed_count": passed_count,
        "error_count": error_count,
        "warning_count": warning_count,
        "pass_rate": pass_rate,
        "average_score": avg_batch_score,
        "items": results,
    }

    record_event(
        db,
        event_type="batch_quality_analyzed",
        entity_type="batch",
        entity_id=batch.id,
        message=f"QC do lote '{batch.name}': {passed_count}/{total_renders} aprovados tecnicamente ({pass_rate}%).",
        payload={
            "total_renders": total_renders,
            "passed_count": passed_count,
            "error_count": error_count,
            "pass_rate": pass_rate,
            "average_score": avg_batch_score,
        },
    )

    return summary

