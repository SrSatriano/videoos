from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import BrandKit
from ..schemas import BrandKitCreate
from ..services.brand_kit import normalize_brand_kit

router = APIRouter(prefix="/api/brand-kits", tags=["brand-kits"])


def brand_kit_to_dict(kit: BrandKit) -> dict:
    return {
        "id": kit.id,
        "name": kit.name,
        "config": json.loads(kit.config_json),
        "is_default": bool(kit.is_default),
        "created_at": kit.created_at.isoformat(),
        "updated_at": kit.updated_at.isoformat(),
    }


@router.get("")
def list_brand_kits(db: Session = Depends(get_db)):
    kits = db.query(BrandKit).order_by(BrandKit.is_default.desc(), BrandKit.created_at.desc()).all()
    return [brand_kit_to_dict(kit) for kit in kits]


@router.post("")
def create_brand_kit(payload: BrandKitCreate, db: Session = Depends(get_db)):
    config = normalize_brand_kit({"name": payload.name, **payload.config})
    if payload.is_default:
        db.query(BrandKit).update({BrandKit.is_default: 0})
    kit = BrandKit(name=payload.name, config_json=json.dumps(config, ensure_ascii=False), is_default=int(payload.is_default))
    db.add(kit)
    db.commit()
    db.refresh(kit)
    return brand_kit_to_dict(kit)


@router.get("/export")
def export_brand_kits(db: Session = Depends(get_db)):
    return {"brand_kits": list_brand_kits(db)}


@router.get("/{kit_id}")
def get_brand_kit(kit_id: str, db: Session = Depends(get_db)):
    kit = db.get(BrandKit, kit_id)
    if not kit:
        raise HTTPException(status_code=404, detail=f"BrandKit '{kit_id}' nao encontrado.")
    return brand_kit_to_dict(kit)


@router.put("/{kit_id}")
def update_brand_kit(kit_id: str, payload: BrandKitCreate, db: Session = Depends(get_db)):
    kit = db.get(BrandKit, kit_id)
    if not kit:
        raise HTTPException(status_code=404, detail=f"BrandKit '{kit_id}' nao encontrado.")
    config = normalize_brand_kit({"name": payload.name, **payload.config})
    if payload.is_default:
        db.query(BrandKit).filter(BrandKit.id != kit_id).update({BrandKit.is_default: 0})
    kit.name = payload.name
    kit.config_json = json.dumps(config, ensure_ascii=False)
    kit.is_default = int(payload.is_default)
    db.commit()
    db.refresh(kit)
    return brand_kit_to_dict(kit)


@router.delete("/{kit_id}")
def delete_brand_kit(kit_id: str, db: Session = Depends(get_db)):
    kit = db.get(BrandKit, kit_id)
    if not kit:
        raise HTTPException(status_code=404, detail=f"BrandKit '{kit_id}' nao encontrado.")
    db.delete(kit)
    db.commit()
    return {"status": "deleted", "id": kit_id}
