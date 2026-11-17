from __future__ import annotations

import math
import shutil
from pathlib import Path

from .. import config
from .path_policy import resolve_allowed_directory


ESTIMATE_BUFFER_RATIO = 0.15
FREE_SPACE_RESERVE_RATIO = 0.10
MIN_FREE_RESERVE_BYTES = 1024**3


def _existing_storage_anchor(path: Path) -> Path:
    candidate = path
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    if not candidate.exists():
        raise ValueError(f"Nao foi possivel localizar o volume da pasta de saida: {path}")
    return candidate if candidate.is_dir() else candidate.parent


def check_storage_capacity(raw_path: str | None, estimated_output_bytes: int) -> dict[str, int | float | bool | str]:
    target = (
        resolve_allowed_directory(raw_path, field_name="output_dir")
        if raw_path and raw_path.strip()
        else config.RENDERS_DIR.resolve()
    )
    usage = shutil.disk_usage(_existing_storage_anchor(target))
    estimate = max(0, int(estimated_output_bytes))
    required_bytes = math.ceil(estimate * (1 + ESTIMATE_BUFFER_RATIO))
    reserve_bytes = min(
        usage.free,
        max(MIN_FREE_RESERVE_BYTES, math.ceil(usage.free * FREE_SPACE_RESERVE_RATIO)),
    )
    safe_available_bytes = max(0, usage.free - reserve_bytes)
    has_capacity = (
        safe_available_bytes > 0
        if estimate == 0
        else (required_bytes <= safe_available_bytes)
    )
    return {
        "path": str(target),
        "total_bytes": usage.total,
        "free_bytes": usage.free,
        "reserve_bytes": reserve_bytes,
        "safe_available_bytes": safe_available_bytes,
        "estimated_output_bytes": estimate,
        "required_bytes": required_bytes,
        "estimate_buffer_ratio": ESTIMATE_BUFFER_RATIO,
        "has_capacity": has_capacity,
    }
