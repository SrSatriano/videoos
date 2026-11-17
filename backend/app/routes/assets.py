from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Asset, AssetProxy
from ..schemas import DeleteAssetsRequest, ImportRequest
from ..serializers import asset_to_dict
from ..services.media import delete_assets, import_file, import_paths, reindex_asset, reindex_assets, save_upload

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("")
def list_assets(
    q: str | None = Query(default=None),
    orientation: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Asset).order_by(Asset.created_at.desc())
    if q:
        query = query.filter(Asset.filename.ilike(f"%{q}%"))
    if orientation:
        query = query.filter(Asset.orientation == orientation)
    return [asset_to_dict(asset) for asset in query.all()]


@router.get("/smart-bins")
def list_smart_bins(db: Session = Depends(get_db)):
    assets = db.query(Asset).order_by(Asset.created_at.desc()).all()
    proxy_asset_ids = {row[0] for row in db.query(AssetProxy.asset_id).all()}

    def collect(predicate):
        return [asset.id for asset in assets if predicate(asset)]

    bins = [
        {
            "id": "all",
            "label": "Todos",
            "description": "Todos os assets importados.",
            "asset_ids": [asset.id for asset in assets],
        },
        {
            "id": "shorts_ready",
            "label": "Prontos para shorts",
            "description": "Verticais, com metadata pronta e ate 3 minutos.",
            "asset_ids": collect(
                lambda asset: asset.orientation == "vertical"
                and asset.metadata_status == "ready"
                and bool(asset.duration_seconds)
                and asset.duration_seconds <= 180
            ),
        },
        {
            "id": "vertical",
            "label": "Verticais",
            "description": "Material 9:16 ou retrato.",
            "asset_ids": collect(lambda asset: asset.orientation == "vertical"),
        },
        {
            "id": "under_60",
            "label": "Ate 60s",
            "description": "Clipes curtos para Reels/TikTok/Shorts.",
            "asset_ids": collect(lambda asset: bool(asset.duration_seconds) and asset.duration_seconds <= 60),
        },
        {
            "id": "long_form",
            "label": "Longos",
            "description": "Material acima de 3 minutos para cortar.",
            "asset_ids": collect(lambda asset: bool(asset.duration_seconds) and asset.duration_seconds > 180),
        },
        {
            "id": "has_proxy",
            "label": "Com proxy",
            "description": "Assets com proxy leve ja gerado.",
            "asset_ids": collect(lambda asset: asset.id in proxy_asset_ids),
        },
        {
            "id": "needs_attention",
            "label": "Atencao",
            "description": "Sem metadata completa ou sem thumbnail.",
            "asset_ids": collect(lambda asset: asset.metadata_status != "ready" or not asset.thumbnail_path),
        },
    ]
    return {"bins": [{**item, "count": len(item["asset_ids"])} for item in bins]}


@router.post("/reindex")
def reindex_asset_library(
    only_attention: bool = Query(default=True),
    force_thumbnail: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    return reindex_assets(db, only_attention=only_attention, force_thumbnail=force_thumbnail)


@router.post("/{asset_id}/reindex")
def reindex_single_asset(asset_id: str, force_thumbnail: bool = Query(default=False), db: Session = Depends(get_db)):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset nao encontrado.")
    result = reindex_asset(db, asset, force_thumbnail=force_thumbnail)
    db.refresh(asset)
    return {"asset": asset_to_dict(asset), "result": result}


@router.post("/import")
def import_assets(payload: ImportRequest, db: Session = Depends(get_db)):
    assets = import_paths(db, payload.paths, copy_to_library=payload.copy_to_library)
    return {
        "imported": [asset_to_dict(asset) for asset in assets],
        "count": len(assets),
    }


@router.post("/delete")
def delete_assets_bulk(payload: DeleteAssetsRequest, db: Session = Depends(get_db)):
    """Remove varios assets da biblioteca de uma vez (arquivos ficam no disco).

    Assets ja usados em lotes/renders sao bloqueados e listados em `skipped`."""
    return delete_assets(db, payload.asset_ids)


@router.delete("/{asset_id}")
def delete_single_asset(asset_id: str, db: Session = Depends(get_db)):
    result = delete_assets(db, [asset_id])
    if result["missing"]:
        raise HTTPException(status_code=404, detail="Asset nao encontrado.")
    if result["skipped"]:
        raise HTTPException(status_code=409, detail=result["skipped"][0]["reason"])
    return result


@router.post("/upload")
async def upload_assets(files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    assets: list[Asset] = []
    for upload in files:
        content = await upload.read()
        saved_path = save_upload(upload.filename or "video.mp4", content)
        assets.append(import_file(db, saved_path, copy_to_library=True))
    return {"imported": [asset_to_dict(asset) for asset in assets], "count": len(assets)}
