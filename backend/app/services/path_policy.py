from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException

from .. import config
from .media import resolve_user_path


def allowed_roots() -> list[Path]:
    return [root.resolve() for root in config.ALLOWED_OUTPUT_ROOTS]


def allowed_roots_message() -> str:
    return ", ".join(str(root) for root in allowed_roots())


def resolve_allowed_directory(raw_path: str, *, field_name: str) -> Path:
    cleaned = raw_path.strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail=f"{field_name} nao pode ficar vazio.")

    candidate = resolve_user_path(cleaned).resolve()
    if not config.path_is_within_roots(candidate, allowed_roots()):
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} fora das pastas permitidas: {allowed_roots_message()}",
        )
    return candidate


def allowed_recipe_media_roots() -> list[Path]:
    return [root.resolve() for root in config.ALLOWED_RECIPE_MEDIA_ROOTS]


def validate_recipe_media_paths(recipe: dict, *, require_existing: bool = False) -> None:
    from .render import validate_recipe
    validate_recipe(recipe, require_existing_media=require_existing)

