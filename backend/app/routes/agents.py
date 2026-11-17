from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import AgentRunRequest, GenerateFacelessVideoRequest, GenerateSceneImageRequest
from ..services.agents import list_agents, run_agent
from ..services.llm import generate_viral_hooks, generate_script_to_video

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("")
def agents():
    return list_agents()


@router.post("/run")
def run(payload: AgentRunRequest):
    return run_agent(payload.agent_id, payload.brief)


@router.post("/viral-hooks")
def api_viral_hooks(payload: dict):
    topic = payload.get("topic", "Dicas e produtividade")
    return generate_viral_hooks(topic)


@router.post("/script-to-video")
def api_script_to_video(payload: dict):
    topic = payload.get("topic", "Dicas e produtividade")
    return generate_script_to_video(topic)


@router.post("/autopilot")
def api_autopilot(payload: dict, db: Session = Depends(get_db)):
    from ..models import Asset, Template, Batch, RenderJob
    asset_id = payload.get("asset_id")
    template_id = payload.get("template_id")
    if not asset_id:
        asset = db.query(Asset).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Nenhum ativo disponivel para o Autopilot.")
        asset_id = asset.id
    if not template_id:
        tpl = db.query(Template).first()
        if not tpl:
            raise HTTPException(status_code=404, detail="Nenhum template cadastrado para o Autopilot.")
        template_id = tpl.id

    variations_count = max(1, min(10, int(payload.get("variations", 3))))
    batch = Batch(
        name=f"Autopilot: {payload.get('name', 'Execucao 1-Clique')}",
        template_id=template_id,
        total_jobs=variations_count,
    )
    db.add(batch)
    db.flush()

    jobs = []
    for idx in range(1, variations_count + 1):
        job = RenderJob(
            batch_id=batch.id,
            asset_id=asset_id,
            template_id=template_id,
            variation_index=idx,
            status="queued",
            current_step="Autopilot: Enfileirado",
        )
        db.add(job)
        jobs.append(job)
    db.commit()
    db.refresh(batch)
    return {
        "status": "success",
        "batch_id": batch.id,
        "total_jobs": len(jobs),
        "steps": [
            "1. Ingestao & Hash SHA-256",
            "2. Transcricao Whisper com Cache",
            "3. AI Clips & Ganchos Virais",
            "4. Dynamic Captions & Safe Zones",
            "5. CTA de 3 Momentos com SFX",
            "6. Render Staging Atomico",
            "7. Quality Check Automatizado",
            "8. Pacote de Publicacao com Checklist",
        ],
    }


@router.post("/generate-faceless-video")
def api_generate_faceless_video(payload: GenerateFacelessVideoRequest, db: Session = Depends(get_db)):
    from pathlib import Path
    import json
    from ..models import Asset, Template, Batch, RenderJob
    from ..services.tts import synthesize_speech
    from ..services.audit import record_event

    script_data: dict = {}
    if payload.script_text and payload.script_text.strip():
        narration = payload.script_text.strip()
        title = payload.video_name or "Vídeo Narrado por IA"
    else:
        topic = payload.topic or "Dicas de Produtividade e Sucesso"
        script_data = generate_script_to_video(topic)
        narration = script_data.get("full_narration") or " ".join(b.get("spoken_text", "") for b in script_data.get("blocks", []))
        title = payload.video_name or script_data.get("title", f"Vídeo IA: {topic}")

    voice_id = payload.voice or "pt-BR-AntonioNeural"
    tts_result = synthesize_speech(narration, voice=voice_id)

    asset = db.query(Asset).first()
    if not asset:
        import hashlib
        audio_path = Path(tts_result["audio_path"])
        asset = Asset(
            filename=audio_path.name,
            original_path=str(audio_path),
            stored_path=str(audio_path),
            sha256=hashlib.sha256(audio_path.name.encode()).hexdigest(),
            size_bytes=audio_path.stat().st_size if audio_path.exists() else 1024,
            duration_seconds=30.0,
            width=1080,
            height=1920,
            orientation="portrait",
            metadata_status="ready",
        )
        db.add(asset)
        db.flush()

    base_tpl = None
    if payload.template_id:
        base_tpl = db.get(Template, payload.template_id)
    if not base_tpl:
        base_tpl = db.query(Template).first()

    recipe: dict = {}
    if base_tpl:
        try:
            recipe = json.loads(base_tpl.recipe_json)
        except Exception:
            recipe = {}

    recipe["format"] = {"width": 1080, "height": 1920, "fit": "crop", "fps": 30}
    if payload.enable_captions and tts_result.get("srt_path"):
        recipe["captions"] = {
            "enabled": True,
            "style": payload.caption_style or "hormozi",
            "burned_srt_path": tts_result["srt_path"],
        }

    if payload.scene_images:
        from ..config import DATA_DIR
        valid_brolls = []
        word_count = len(narration.split())
        est_duration = max(15.0, round(word_count / 2.5, 1))
        seg_duration = round(est_duration / len(payload.scene_images), 2)
        for i, img_ref in enumerate(payload.scene_images):
            img_path = None
            if "/media/" in img_ref:
                rel = img_ref.split("/media/", 1)[1]
                p = (DATA_DIR / rel).resolve()
                if p.exists():
                    img_path = str(p)
            elif Path(img_ref).exists():
                img_path = str(Path(img_ref).resolve())

            if img_path:
                start_t = round(i * seg_duration, 2)
                end_t = round((i + 1) * seg_duration, 2)
                valid_brolls.append({
                    "path": img_path,
                    "start": start_t,
                    "end": end_t,
                    "layout": "cover",
                    "opacity": 1.0,
                })
        if valid_brolls:
            recipe["broll"] = valid_brolls

    derived_tpl = Template(
        name=f"Template IA: {title[:40]}",
        description=f"Template para vídeo gerado com voz neural {voice_id}",
        recipe_json=json.dumps(recipe, ensure_ascii=False),
    )
    db.add(derived_tpl)
    db.flush()

    batch = Batch(
        name=f"Faceless IA: {title[:50]}",
        template_id=derived_tpl.id,
        total_jobs=1,
    )
    db.add(batch)
    db.flush()

    job = RenderJob(
        batch_id=batch.id,
        asset_id=asset.id,
        template_id=derived_tpl.id,
        variation_index=1,
        status="queued",
        current_step="Na fila para renderizacao do video gerado por IA",
    )
    db.add(job)
    db.commit()
    db.refresh(batch)

    record_event(
        db,
        event_type="faceless_video_generated",
        entity_type="batch",
        entity_id=batch.id,
        message=f"Vídeo de IA '{title}' criado com locução neural e legendas.",
        payload={"batch_id": batch.id, "job_id": job.id, "voice": voice_id},
    )

    return {
        "status": "success",
        "batch_id": batch.id,
        "job_id": job.id,
        "title": title,
        "narration": narration,
        "tts": tts_result,
        "script": script_data,
    }


@router.post("/generate-scene-image")
def api_generate_scene_image(
    payload: GenerateSceneImageRequest,
    db: Session = Depends(get_db),
):
    from pathlib import Path
    import hashlib
    from ..models import Asset
    from ..services.image_gen import generate_scene_image
    from ..services.audit import record_event

    result = generate_scene_image(
        prompt=payload.prompt,
        aspect_ratio=payload.aspect_ratio,
        provider=payload.provider,
    )

    asset_id = None
    if payload.save_as_asset:
        target_path = Path(result["image_path"])
        existing = db.query(Asset).filter(Asset.filename == result["filename"]).first()
        if not existing:
            sha256 = hashlib.sha256(result["filename"].encode("utf-8")).hexdigest()
            asset = Asset(
                filename=result["filename"],
                original_path=str(target_path),
                stored_path=str(target_path),
                sha256=sha256,
                size_bytes=result.get("size_bytes", 1024),
                duration_seconds=5.0,
                width=result.get("width", 1080),
                height=result.get("height", 1920),
                orientation="portrait" if result.get("height", 1920) > result.get("width", 1080) else "landscape",
                metadata_status="ready",
            )
            db.add(asset)
            db.commit()
            db.refresh(asset)
            asset_id = asset.id
        else:
            asset_id = existing.id

    result["asset_id"] = asset_id

    record_event(
        db,
        event_type="scene_image_generated",
        entity_type="asset",
        entity_id=asset_id or "ephemeral",
        message=f"Imagem gerada via IA ({result.get('provider')}) para o prompt: '{payload.prompt[:50]}...'",
        payload={"prompt": payload.prompt, "provider": result.get("provider")},
    )

    return result


