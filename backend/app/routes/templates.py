from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Batch, RenderJob, Template
from ..schemas import TemplateCreate, TemplateDuplicateRequest, TemplateUpdate
from ..serializers import template_to_dict
from ..services.audit import record_event
from ..services.render import validate_recipe

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("")
def list_templates(db: Session = Depends(get_db)):
    return [template_to_dict(template) for template in db.query(Template).order_by(Template.created_at.desc()).all()]


@router.post("")
def create_template(payload: TemplateCreate, db: Session = Depends(get_db)):
    try:
        validate_recipe(payload.recipe)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    template = Template(
        name=payload.name,
        description=payload.description,
        recipe_json=json.dumps(payload.recipe, ensure_ascii=False),
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    record_event(
        db,
        event_type="template_created",
        entity_type="template",
        entity_id=template.id,
        message=f"Template criado: {template.name}.",
    )
    return template_to_dict(template)


@router.get("/export")
def export_templates(db: Session = Depends(get_db)):
    templates = db.query(Template).order_by(Template.name.asc()).all()
    return {"templates": [template_to_dict(template) for template in templates]}


@router.get("/{template_id}")
def get_template(template_id: str, db: Session = Depends(get_db)):
    template = db.get(Template, template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' nao encontrado.")
    return template_to_dict(template)


@router.put("/{template_id}")
def update_template(template_id: str, payload: TemplateUpdate, db: Session = Depends(get_db)):
    template = db.get(Template, template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' nao encontrado.")

    if payload.recipe is not None:
        try:
            validate_recipe(payload.recipe)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        template.recipe_json = json.dumps(payload.recipe, ensure_ascii=False)

    if payload.name is not None:
        template.name = payload.name
    if payload.description is not None:
        template.description = payload.description

    db.commit()
    db.refresh(template)
    record_event(
        db,
        event_type="template_updated",
        entity_type="template",
        entity_id=template.id,
        message=f"Template atualizado: {template.name}.",
    )
    return template_to_dict(template)


@router.delete("/{template_id}")
def delete_template(template_id: str, db: Session = Depends(get_db)):
    template = db.get(Template, template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' nao encontrado.")

    in_use_batches = db.query(Batch).filter(Batch.template_id == template_id).count()
    in_use_jobs = db.query(RenderJob).filter(RenderJob.template_id == template_id).count()
    if in_use_batches > 0 or in_use_jobs > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Template em uso por {in_use_batches} lote(s) e {in_use_jobs} renderizacao(oes). Nao pode ser excluido.",
        )

    template_name = template.name
    db.delete(template)
    db.commit()
    record_event(
        db,
        event_type="template_deleted",
        entity_type="template",
        entity_id=template_id,
        message=f"Template excluido: {template_name}.",
    )
    return {"status": "deleted", "id": template_id}


@router.post("/{template_id}/duplicate")
def duplicate_template(
    template_id: str,
    payload: TemplateDuplicateRequest | None = None,
    db: Session = Depends(get_db),
):
    source = db.get(Template, template_id)
    if not source:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' nao encontrado.")

    new_name = (payload.name if payload and payload.name else f"{source.name} (Copia)")[:120]
    duplicate = Template(
        name=new_name,
        description=source.description,
        recipe_json=source.recipe_json,
    )
    db.add(duplicate)
    db.commit()
    db.refresh(duplicate)
    record_event(
        db,
        event_type="template_duplicated",
        entity_type="template",
        entity_id=duplicate.id,
        message=f"Template duplicado: {duplicate.name} (origem: {source.id}).",
    )
    return template_to_dict(duplicate)

