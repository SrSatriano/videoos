from __future__ import annotations

import base64
import hashlib
import json
import logging
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from ..config import BROLL_DIR, GOOGLE_API_KEY

logger = logging.getLogger(__name__)

# Fallback JPEG 1x1 pixel binário seguro caso a máquina esteja sem conexão externa
MINIMAL_VALID_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00"
    b"\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19"
    b"\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'"
    b"9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00"
    b"\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03"
    b"\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
)


def _generate_with_google_imagen(prompt: str, aspect_ratio: str, target_path: Path) -> bool:
    """Gera imagem usando Google Imagen 3 API via REST."""
    if not GOOGLE_API_KEY:
        return False

    url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={GOOGLE_API_KEY}"
    ar = "9:16" if aspect_ratio == "9:16" else "16:9" if aspect_ratio == "16:9" else "1:1"
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": ar,
            "personGeneration": "ALLOW_ADULT",
        },
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                predictions = data.get("predictions", [])
                if predictions and "bytesBase64Encoded" in predictions[0]:
                    img_bytes = base64.b64decode(predictions[0]["bytesBase64Encoded"])
                    with open(target_path, "wb") as f:
                        f.write(img_bytes)
                    return True
    except Exception as exc:
        logger.warning("Falha na chamada ao Google Imagen 3: %s. Acionando fallback.", exc)
    return False


def _generate_with_pollinations(prompt: str, width: int, height: int, target_path: Path, seed: int) -> bool:
    """Gera imagem usando Pollinations AI (FLUX) sem necessidade de chave de API."""
    encoded_prompt = urllib.parse.quote(prompt[:300])
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux&nologo=true&seed={seed}"

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "VideoOS/1.0 (Automation Studio)"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status == 200:
                data = response.read()
                if len(data) > 1024:
                    with open(target_path, "wb") as f:
                        f.write(data)
                    return True
    except Exception as exc:
        logger.warning("Falha na chamada ao Pollinations AI: %s. Acionando fallback defensivo.", exc)
    return False


def generate_scene_image(
    prompt: str,
    aspect_ratio: str = "9:16",
    provider: str = "auto",
) -> dict[str, Any]:
    """Gera imagem de cena vertical ou horizontal a partir de prompt com fallback defensivo."""
    clean_prompt = prompt.strip()
    if not clean_prompt:
        raise ValueError("O prompt para geração de imagem não pode ser vazio.")

    width, height = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080) if aspect_ratio == "16:9" else (1080, 1080)

    file_hash = hashlib.md5(f"{clean_prompt}:{aspect_ratio}".encode("utf-8")).hexdigest()[:12]
    filename = f"gen_img_{file_hash}.jpg"
    target_path = BROLL_DIR / filename

    # Se já existir em cache e for válido (>1KB), retorna imediatamente
    if target_path.exists() and target_path.stat().st_size > 1024:
        return {
            "status": "success",
            "image_path": str(target_path),
            "image_url": f"/media/broll/{filename}",
            "filename": filename,
            "prompt": clean_prompt,
            "provider": "cache",
            "width": width,
            "height": height,
            "size_bytes": target_path.stat().st_size,
        }

    provider_used = "fallback"

    # 1. Tentar Google Imagen se solicitado ou auto
    if provider in ("auto", "google") and GOOGLE_API_KEY:
        if _generate_with_google_imagen(clean_prompt, aspect_ratio, target_path):
            provider_used = "google_imagen"

    # 2. Tentar Pollinations AI (FLUX) se ainda não gerou
    if provider_used == "fallback" and provider in ("auto", "pollinations", "google"):
        seed = int(file_hash, 16) % 1000000
        if _generate_with_pollinations(clean_prompt, width, height, target_path, seed):
            provider_used = "pollinations_flux"

    # 3. Fallback defensivo garantindo que o arquivo exista
    if not target_path.exists() or target_path.stat().st_size == 0:
        with open(target_path, "wb") as f:
            f.write(MINIMAL_VALID_JPEG)
        provider_used = "defensive_fallback"

    return {
        "status": "success",
        "image_path": str(target_path),
        "image_url": f"/media/broll/{filename}",
        "filename": filename,
        "prompt": clean_prompt,
        "provider": provider_used,
        "width": width,
        "height": height,
        "size_bytes": target_path.stat().st_size,
    }
