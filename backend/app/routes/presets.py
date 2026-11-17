from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Template
from ..serializers import template_to_dict
from ..services.preset_library import preset_library, template_presets
from ..services.render import validate_recipe

router = APIRouter(prefix="/api/preset-library", tags=["preset-library"])


@router.get("")
def list_preset_library():
    return preset_library()


@router.post("/templates/{preset_id}/install")
def install_template_preset(preset_id: str, db: Session = Depends(get_db)):
    preset = next((item for item in template_presets() if item["id"] == preset_id), None)
    if not preset:
        raise HTTPException(status_code=404, detail="Preset de template nao encontrado.")
    validate_recipe(preset["recipe"])
    template = Template(
        name=preset["name"],
        description=preset["description"],
        recipe_json=json.dumps(preset["recipe"], ensure_ascii=False),
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template_to_dict(template)
