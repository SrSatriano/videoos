from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Asset, ClipCandidate, Template, Transcript
from ..schemas import (
    AutopilotPipelineRequest,
    BatchCreate,
    ClipAnalyzeRequest,
    ClipBatchRequest,
    CreateBatchFromClipsRequest,
    MineViralClipsRequest,
)
from ..serializers import batch_to_dict, template_to_dict
from ..services.clip_analysis import split_transcript_into_candidates
from ..services.queue import create_batch

router = APIRouter(prefix="/api/clips", tags=["clips"])


def clip_to_dict(clip: ClipCandidate) -> dict:
    return {
        "id": clip.id,
        "asset_id": clip.asset_id,
        "transcript_id": clip.transcript_id,
        "start_seconds": clip.start_seconds,
        "end_seconds": clip.end_seconds,
        "score": clip.score,
        "hook": clip.hook,
        "reason": clip.reason,
        "status": clip.status,
        "created_at": clip.created_at.isoformat(),
    }


@router.get("")
def list_clips(db: Session = Depends(get_db)):
    clips = db.query(ClipCandidate).order_by(ClipCandidate.score.desc(), ClipCandidate.created_at.desc()).limit(100).all()
    return [clip_to_dict(clip) for clip in clips]


@router.post("/analyze")
def analyze(payload: ClipAnalyzeRequest, db: Session = Depends(get_db)):
    asset = db.get(Asset, payload.asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset nao encontrado.")
    transcript = (
        db.query(Transcript)
        .filter(Transcript.asset_id == payload.asset_id)
        .order_by(Transcript.created_at.desc())
        .first()
    )
    if transcript:
        segments = json.loads(transcript.segments_json)
    else:
        duration = asset.duration_seconds or payload.max_seconds
        segments = [
            {
                "start": 0,
                "end": min(float(duration), float(payload.max_seconds)),
                "text": f"{asset.filename} - trecho sugerido para hook e CTA",
            }
        ]
    candidates = split_transcript_into_candidates(segments, payload.min_seconds, payload.max_seconds)[: payload.limit]
    created = []
    for candidate in candidates:
        clip = ClipCandidate(asset_id=asset.id, transcript_id=transcript.id if transcript else None, **candidate)
        db.add(clip)
        created.append(clip)
    db.commit()
    for clip in created:
        db.refresh(clip)
    return [clip_to_dict(clip) for clip in created]


@router.post("/{clip_id}/create-batch")
def create_batch_from_clip(clip_id: str, payload: ClipBatchRequest, db: Session = Depends(get_db)):
    clip = db.get(ClipCandidate, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Corte sugerido nao encontrado.")
    template = db.get(Template, payload.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template nao encontrado.")

    recipe = json.loads(template.recipe_json)
    recipe["trim"] = {"start": clip.start_seconds, "end": clip.end_seconds}
    derived = Template(
        name=f"{template.name} - corte {clip.id[:6]}",
        description=f"Template derivado de corte sugerido {clip.start_seconds:g}s-{clip.end_seconds:g}s.",
        recipe_json=json.dumps(recipe, ensure_ascii=False),
    )
    db.add(derived)
    db.commit()
    db.refresh(derived)

    batch = create_batch(
        db,
        BatchCreate(
            name=payload.name or f"Corte {clip.id[:6]}",
            template_id=derived.id,
            asset_ids=[clip.asset_id],
            variations=payload.variations,
        ),
    )
    db.refresh(batch)
    return {"clip": clip_to_dict(clip), "template": template_to_dict(derived), "batch": batch_to_dict(batch)}


@router.get("/assets/{asset_id}")
def get_asset_clips(asset_id: str, db: Session = Depends(get_db)):
    candidates = (
        db.query(ClipCandidate)
        .filter(ClipCandidate.asset_id == asset_id)
        .order_by(ClipCandidate.score.desc())
        .all()
    )
    return [clip_to_dict(c) for c in candidates]


@router.post("/assets/{asset_id}/mine-viral")
def mine_viral_clips_for_asset(
    asset_id: str,
    payload: MineViralClipsRequest | None = None,
    db: Session = Depends(get_db),
):
    from ..config import GOOGLE_API_KEY
    from ..services.audit import record_event
    from ..services.llm import analyze_viral_clips_with_ai

    req = payload or MineViralClipsRequest()
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset nao encontrado.")

    transcript = db.query(Transcript).filter(Transcript.asset_id == asset.id).first()
    transcript_text = ""
    segments: list[dict] = []

    if transcript and transcript.text:
        transcript_text = transcript.text
        if transcript.segments_json:
            try:
                segments = json.loads(transcript.segments_json)
            except Exception:
                segments = []
    else:
        try:
            from ..services.transcription import transcribe_asset
            res = transcribe_asset(asset)
            transcript_text = res.get("text", "")
            segments = res.get("segments", [])
        except Exception:
            transcript_text = asset.filename or "Video sem fala"
            segments = []

    if not segments:
        duration = asset.duration_seconds or 60.0
        step = min(float(req.max_seconds), max(float(req.min_seconds), 20.0))
        cur = 0.0
        idx = 1
        while cur + 10.0 <= duration:
            end_t = min(cur + step, duration)
            segments.append({
                "start": cur,
                "end": end_t,
                "text": f"Segmento {idx} do video {asset.filename}",
            })
            cur += step * 0.7
            idx += 1

    mined_clips = analyze_viral_clips_with_ai(
        transcript_text=transcript_text,
        segments=segments,
        min_seconds=req.min_seconds,
        max_seconds=req.max_seconds,
        target_count=req.target_count,
    )

    saved_candidates = []
    for item in mined_clips:
        cand = ClipCandidate(
            asset_id=asset.id,
            transcript_id=transcript.id if transcript else None,
            start_seconds=item["start_seconds"],
            end_seconds=item["end_seconds"],
            score=round(item["viral_score"] / 100.0, 3),
            hook=item["hook"][:200],
            reason=item.get("reason", "")[:1000],
            status="suggested",
        )
        db.add(cand)
        db.flush()
        item["id"] = cand.id
        saved_candidates.append(item)

    db.commit()

    record_event(
        db,
        event_type="viral_clips_mined",
        entity_type="asset",
        entity_id=asset.id,
        message=f"{len(saved_candidates)} cortes virais minerados com sucesso.",
        payload={"asset_id": asset.id, "count": len(saved_candidates)},
    )

    return {
        "asset_id": asset.id,
        "engine": "google-gemini-2.0-flash" if GOOGLE_API_KEY else "heuristic-virality-engine",
        "count": len(saved_candidates),
        "clips": saved_candidates,
    }


@router.post("/batch-create")
def create_batch_from_clips_route(payload: CreateBatchFromClipsRequest, db: Session = Depends(get_db)):
    from ..models import Batch, RenderJob
    from ..services.audit import record_event

    asset = db.get(Asset, payload.asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset nao encontrado.")

    base_template = db.get(Template, payload.template_id)
    if not base_template:
        raise HTTPException(status_code=404, detail="Template nao encontrado.")

    if not payload.clips:
        raise HTTPException(status_code=400, detail="Nenhum corte selecionado.")

    batch_name = payload.batch_name.strip() or f"Cortes Virais - {asset.filename[:30]}"
    batch = Batch(
        name=batch_name,
        template_id=base_template.id,
        status="queued",
        total_jobs=len(payload.clips),
    )
    db.add(batch)
    db.flush()

    for idx, clip in enumerate(payload.clips, 1):
        try:
            recipe = json.loads(base_template.recipe_json)
        except Exception:
            recipe = {}

        recipe["trim"] = {
            "start": float(clip["start_seconds"]),
            "end": float(clip["end_seconds"]),
        }

        # Aplicar opções condicionais de edição solicitadas pelo criador
        if payload.enable_captions:
            captions_cfg = recipe.get("captions", {})
            captions_cfg["enabled"] = True
            captions_cfg["style"] = payload.caption_style
            from ..config import TRANSCRIPTS_DIR
            candidate_srt = TRANSCRIPTS_DIR / asset.id / "transcript.srt"
            if candidate_srt.exists():
                captions_cfg["burned_srt_path"] = str(candidate_srt)
            recipe["captions"] = captions_cfg
        else:
            if "captions" in recipe:
                recipe["captions"]["enabled"] = False

        if payload.enable_jumpcut:
            jumpcut_cfg = recipe.get("jump_cut", {})
            jumpcut_cfg["enabled"] = True
            jumpcut_cfg["min_silence_duration"] = 0.4
            recipe["jump_cut"] = jumpcut_cfg
        else:
            if "jump_cut" in recipe:
                recipe["jump_cut"]["enabled"] = False

        if payload.enable_music:
            ducking_cfg = recipe.get("audio_ducking", {})
            ducking_cfg["enabled"] = True
            ducking_cfg["music_volume"] = float(payload.music_volume)
            recipe["audio_ducking"] = ducking_cfg
        else:
            if "audio_ducking" in recipe:
                recipe["audio_ducking"]["enabled"] = False

        if clip.get("suggested_title"):
            text_layers = recipe.get("text_layers", [])
            for layer in text_layers:
                if layer.get("type") in ("headline", "title", "hook"):
                    layer["text"] = clip["suggested_title"]

        clip_template = Template(
            name=f"{base_template.name} - Corte #{idx} ({clip['start_seconds']}s-{clip['end_seconds']}s)",
            description=f"Template gerado automaticamente para corte viral de {asset.filename}",
            recipe_json=json.dumps(recipe, ensure_ascii=False),
        )
        db.add(clip_template)
        db.flush()

        job = RenderJob(
            batch_id=batch.id,
            asset_id=asset.id,
            template_id=clip_template.id,
            variation_index=idx,
            status="queued",
            progress=0,
            current_step="Na fila para renderizacao do corte",
        )
        db.add(job)

    db.commit()
    db.refresh(batch)

    record_event(
        db,
        event_type="batch_created_from_viral_clips",
        entity_type="batch",
        entity_id=batch.id,
        message=f"Lote criado a partir de {len(payload.clips)} cortes virais.",
        payload={"batch_id": batch.id, "clip_count": len(payload.clips)},
    )

    return batch_to_dict(batch)


@router.post("/autopilot")
def api_autopilot_pipeline(
    payload: AutopilotPipelineRequest,
    db: Session = Depends(get_db),
):
    from ..config import TRANSCRIPTS_DIR
    from ..models import Batch, RenderJob
    from ..services.audit import record_event
    from ..services.llm import analyze_viral_clips_with_ai

    # 1. Obter ou resolver o asset
    asset = None
    if payload.asset_id:
        asset = db.get(Asset, payload.asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset não encontrado para o Piloto Automático.")
    elif payload.source_url:
        clean_url = payload.source_url.strip()
        asset = db.query(Asset).filter(Asset.original_path.contains(clean_url)).first()
        if not asset:
            asset = db.query(Asset).first()
    else:
        asset = db.query(Asset).first()

    if not asset:
        raise HTTPException(status_code=400, detail="Nenhum asset disponível para o Piloto Automático. Faça upload ou selecione um vídeo.")

    # 2. Obter ou gerar transcrição
    transcript = db.query(Transcript).filter(Transcript.asset_id == asset.id).first()
    transcript_text = ""
    segments: list[dict] = []
    if transcript and transcript.text:
        transcript_text = transcript.text
        if transcript.segments_json:
            try:
                segments = json.loads(transcript.segments_json)
            except Exception:
                segments = []

    # 3. Minerar cortes virais com IA
    mined_clips = analyze_viral_clips_with_ai(
        transcript_text=transcript_text,
        segments=segments,
        min_seconds=15,
        max_seconds=60,
        target_count=max(payload.max_clips + 2, 5),
    )

    # 4. Filtrar por score
    selected_clips = [c for c in mined_clips if c.get("viral_score", 0) >= payload.min_score]
    if not selected_clips:
        selected_clips = sorted(mined_clips, key=lambda c: c.get("viral_score", 0), reverse=True)[:payload.max_clips]
    else:
        selected_clips = selected_clips[:payload.max_clips]

    if not selected_clips:
        dur = float(asset.duration_seconds or 30.0)
        selected_clips = [{
            "start_seconds": 0.0,
            "end_seconds": min(30.0, dur),
            "duration": min(30.0, dur),
            "viral_score": 85,
            "hook": "Assista até o fim para entender isso!",
            "suggested_title": f"Destaque Viral - {asset.filename[:30]}",
            "suggested_copy": "Você não vai acreditar no que aconteceu aqui!",
            "suggested_hashtags": ["#viral", "#shorts", "#fyp"],
        }]

    # 5. Obter template base 9:16
    base_template = db.query(Template).first()
    if not base_template:
        base_template = Template(
            name="Template Vertical 9:16 Padrão",
            description="Template vertical automático",
            recipe_json=json.dumps({"format": {"width": 1080, "height": 1920, "fit": "crop", "fps": 30}}),
        )
        db.add(base_template)
        db.flush()

    # 6. Criar Batch
    batch_name = payload.batch_name or f"Piloto Automático: {asset.filename[:35]}"
    batch = Batch(
        name=batch_name,
        template_id=base_template.id,
        status="queued",
        total_jobs=len(selected_clips),
    )
    db.add(batch)
    db.flush()

    # 7. Criar Jobs com as diretrizes condicionais de edição
    jobs = []
    for idx, clip in enumerate(selected_clips, 1):
        try:
            recipe = json.loads(base_template.recipe_json)
        except Exception:
            recipe = {}

        recipe["trim"] = {
            "start": float(clip["start_seconds"]),
            "end": float(clip["end_seconds"]),
        }
        recipe["format"] = {"width": 1080, "height": 1920, "fit": "crop", "fps": 30}

        if payload.enable_captions:
            captions_cfg = recipe.get("captions", {})
            captions_cfg["enabled"] = True
            captions_cfg["style"] = payload.caption_style
            candidate_srt = TRANSCRIPTS_DIR / asset.id / "transcript.srt"
            if candidate_srt.exists():
                captions_cfg["burned_srt_path"] = str(candidate_srt)
            recipe["captions"] = captions_cfg
        else:
            if "captions" in recipe:
                recipe["captions"]["enabled"] = False

        if payload.enable_jumpcut:
            jumpcut_cfg = recipe.get("jump_cut", {})
            jumpcut_cfg["enabled"] = True
            jumpcut_cfg["min_silence_duration"] = 0.4
            recipe["jump_cut"] = jumpcut_cfg
        else:
            if "jump_cut" in recipe:
                recipe["jump_cut"]["enabled"] = False

        if payload.enable_music:
            ducking_cfg = recipe.get("audio_ducking", {})
            ducking_cfg["enabled"] = True
            ducking_cfg["music_volume"] = float(payload.music_volume)
            recipe["audio_ducking"] = ducking_cfg
        else:
            if "audio_ducking" in recipe:
                recipe["audio_ducking"]["enabled"] = False

        if clip.get("suggested_title"):
            text_layers = recipe.get("text_layers", [])
            for layer in text_layers:
                if layer.get("type") in ("headline", "title", "hook"):
                    layer["text"] = clip["suggested_title"]

        clip_template = Template(
            name=f"Autopilot - Corte #{idx} ({clip['start_seconds']}s-{clip['end_seconds']}s)",
            description=f"Template gerado pelo Piloto Automático para {asset.filename}",
            recipe_json=json.dumps(recipe, ensure_ascii=False),
        )
        db.add(clip_template)
        db.flush()

        job = RenderJob(
            batch_id=batch.id,
            asset_id=asset.id,
            template_id=clip_template.id,
            variation_index=idx,
            status="queued",
            progress=0,
            current_step="Na fila para renderização automática (Piloto Automático)",
        )
        db.add(job)
        jobs.append(job)

    db.commit()
    db.refresh(batch)

    record_event(
        db,
        event_type="autopilot_pipeline_completed",
        entity_type="batch",
        entity_id=batch.id,
        message=f"Piloto Automático concluiu: {len(selected_clips)} cortes 9:16 gerados e enfileirados.",
        payload={"batch_id": batch.id, "total_jobs": len(jobs), "asset_id": asset.id},
    )

    return {
        "status": "success",
        "batch_id": batch.id,
        "batch_name": batch.name,
        "asset": {
            "id": asset.id,
            "filename": asset.filename,
            "duration": asset.duration_seconds,
        },
        "total_jobs": len(jobs),
        "clips_evaluated": len(mined_clips),
        "clips_selected": len(selected_clips),
        "clips": selected_clips,
        "conditional_editing": {
            "captions": payload.enable_captions,
            "caption_style": payload.caption_style,
            "music": payload.enable_music,
            "music_volume": payload.music_volume,
            "jumpcut": payload.enable_jumpcut,
        },
    }

