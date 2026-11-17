from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryFile
from time import monotonic
from typing import Any, Callable

from ..config import ALLOWED_RECIPE_MEDIA_ROOTS, APP_ROOT, RENDER_TIMEOUT_SECONDS, VIDEO_EXTENSIONS, path_is_within_roots
from .media import ensure_ffmpeg, ffprobe_metadata, generate_thumbnail, resolve_user_path


CAPTION_EXTENSIONS = {".srt", ".vtt", ".ass", ".ssa"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
AUDIO_EXTENSIONS = {".aac", ".flac", ".m4a", ".mp3", ".ogg", ".wav"}
BROLL_LAYOUTS = {"cover", "contain"}
FRAME_VIDEO_FITS = {"crop", "contain", "blur_pad"}


class RenderCanceledError(RuntimeError):
    pass


def _process_rss_bytes(pid: int) -> int | None:
    status_path = Path(f"/proc/{pid}/status")
    try:
        status = status_path.read_text(encoding="utf-8")
    except OSError:
        status = ""
    for label in ("VmHWM:", "VmRSS:"):
        for line in status.splitlines():
            if not line.startswith(label):
                continue
            parts = line.split()
            if len(parts) < 2:
                return None
            try:
                value = int(parts[1])
            except ValueError:
                return None
            unit = parts[2].lower() if len(parts) > 2 else "bytes"
            multiplier = {"kb": 1024, "mb": 1024**2, "gb": 1024**3}.get(unit, 1)
            return value * multiplier

    if os.name != "nt":
        return None

    try:
        import ctypes
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        psapi.GetProcessMemoryInfo.argtypes = (
            wintypes.HANDLE,
            ctypes.POINTER(ProcessMemoryCounters),
            wintypes.DWORD,
        )
        handle = kernel32.OpenProcess(0x1000 | 0x0010, False, pid)
        if not handle:
            return None
        try:
            counters = ProcessMemoryCounters()
            counters.cb = ctypes.sizeof(counters)
            if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
                return None
            return int(counters.PeakWorkingSetSize)
        finally:
            kernel32.CloseHandle(handle)
    except (AttributeError, OSError, ValueError):
        return None


def _terminate_process(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run_ffmpeg_command(
    command: list[str],
    *,
    should_cancel: Callable[[], bool] | None = None,
) -> subprocess.CompletedProcess[str]:
    deadline = monotonic() + RENDER_TIMEOUT_SECONDS
    with TemporaryFile(mode="w+t", encoding="utf-8") as stderr_file:
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=stderr_file,
            text=True,
            encoding="utf-8",
        )
        peak_rss_bytes = 0
        try:
            while process.poll() is None:
                sample = _process_rss_bytes(process.pid)
                if sample and sample > peak_rss_bytes:
                    peak_rss_bytes = sample
                if should_cancel and should_cancel():
                    _terminate_process(process)
                    raise RenderCanceledError("Render cancelado pelo usuario.")
                remaining = deadline - monotonic()
                if remaining <= 0:
                    _terminate_process(process)
                    raise subprocess.TimeoutExpired(command, RENDER_TIMEOUT_SECONDS)
                try:
                    process.wait(timeout=min(0.25, remaining))
                except subprocess.TimeoutExpired:
                    continue
            if should_cancel and should_cancel():
                raise RenderCanceledError("Render cancelado pelo usuario.")
        except BaseException:
            _terminate_process(process)
            raise

        stderr_file.seek(0)
        stderr = stderr_file.read()
    completed = subprocess.CompletedProcess(command, process.returncode, "", stderr)
    completed.peak_rss_bytes = peak_rss_bytes or None
    return completed


def load_recipe(recipe_json: str) -> dict[str, Any]:
    recipe = json.loads(recipe_json)
    validate_recipe(recipe, require_existing_media=True)
    return normalize_recipe_media_paths(recipe, require_existing_media=True)


def recipe_media_roots() -> list[Path]:
    return [root.resolve() for root in ALLOWED_RECIPE_MEDIA_ROOTS]


def recipe_media_roots_message() -> str:
    return ", ".join(str(root) for root in recipe_media_roots())


def resolve_recipe_media_path(
    raw_path: Any,
    *,
    field_name: str,
    allowed_extensions: set[str],
    require_existing_media: bool,
) -> Path:
    cleaned = str(raw_path or "").strip()
    if not cleaned:
        raise ValueError(f"{field_name} nao pode ficar vazio.")

    candidate = resolve_user_path(cleaned)
    if not candidate.is_absolute():
        candidate = APP_ROOT / candidate
    candidate = candidate.resolve()

    if not path_is_within_roots(candidate, recipe_media_roots()):
        raise ValueError(f"{field_name} fora das pastas permitidas: {recipe_media_roots_message()}")
    if candidate.suffix.lower() not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise ValueError(f"{field_name} deve usar uma extensao permitida: {allowed}")
    if require_existing_media and not candidate.is_file():
        raise ValueError(f"{field_name} nao encontrado: {candidate}")
    return candidate


def validate_recipe(recipe: dict[str, Any], *, require_existing_media: bool = False) -> None:
    fmt = recipe.get("format", {})
    width = int(fmt.get("width", 1080))
    height = int(fmt.get("height", 1920))
    if width <= 0 or height <= 0:
        raise ValueError("Dimensoes de exportacao invalidas.")
    if abs((width / height) - (9 / 16)) > 0.02:
        raise ValueError("O MVP aceita apenas receitas verticais 9:16.")
    if fmt.get("fit", "crop") not in {"crop", "contain"}:
        raise ValueError("fit deve ser crop ou contain.")
    fps = fmt.get("fps")
    if fps is not None and float(fps) <= 0:
        raise ValueError("fps deve ser maior que zero.")
    trim = recipe.get("trim", {})
    start = trim.get("start")
    end = trim.get("end")
    if end not in (None, "") and start not in (None, "") and float(end) <= float(start):
        raise ValueError("trim.end deve ser maior que trim.start.")
    captions = recipe.get("captions", {})
    if captions.get("enabled") and str(captions.get("burned_srt_path", "")).strip():
        resolve_recipe_media_path(
            captions["burned_srt_path"],
            field_name="captions.burned_srt_path",
            allowed_extensions=CAPTION_EXTENSIONS,
            require_existing_media=require_existing_media,
        )

    for index, item in enumerate(recipe.get("broll", []) or []):
        field_name = f"broll[{index}].path"
        resolve_recipe_media_path(
            item.get("path"),
            field_name=field_name,
            allowed_extensions=VIDEO_EXTENSIONS,
            require_existing_media=require_existing_media,
        )
        item_start = float(item.get("start", 0))
        item_end = float(item.get("end", item_start + 5))
        if item_end <= item_start:
            raise ValueError(f"broll[{index}].end deve ser maior que broll[{index}].start.")
        if item.get("layout", "cover") not in BROLL_LAYOUTS:
            raise ValueError(f"broll[{index}].layout deve ser cover ou contain.")

    frame = recipe.get("frame", {}) or {}
    if frame.get("enabled"):
        header_height = int(frame.get("header_height", max(220, round(height * 0.18))))
        divider_height = int(frame.get("divider_height", max(4, round(height * 0.004))))
        video_margin = int(frame.get("video_margin", 0))
        logo_size = int(frame.get("logo_size", max(80, round(header_height * 0.48))))
        if header_height < 80 or header_height >= height - 120:
            raise ValueError("frame.header_height deve deixar espaco util para o video.")
        if divider_height < 0 or divider_height > 80:
            raise ValueError("frame.divider_height invalido.")
        if video_margin < 0 or video_margin > min(width, height) // 5:
            raise ValueError("frame.video_margin invalido.")
        if logo_size <= 0 or logo_size > header_height:
            raise ValueError("frame.logo_size deve caber no cabecalho.")
        if frame.get("video_fit", "crop") not in FRAME_VIDEO_FITS:
            raise ValueError("frame.video_fit deve ser crop, contain ou blur_pad.")
        if str(frame.get("logo_path", "")).strip():
            resolve_recipe_media_path(
                frame["logo_path"],
                field_name="frame.logo_path",
                allowed_extensions=IMAGE_EXTENSIONS,
                require_existing_media=require_existing_media,
            )

    audio = recipe.get("audio", {}) or {}
    if str(audio.get("music_path", "")).strip():
        resolve_recipe_media_path(
            audio["music_path"],
            field_name="audio.music_path",
            allowed_extensions=AUDIO_EXTENSIONS,
            require_existing_media=require_existing_media,
        )

    split = recipe.get("split", {}) or {}
    if str(split.get("secondary_video_path", "")).strip():
        resolve_recipe_media_path(
            split["secondary_video_path"],
            field_name="split.secondary_video_path",
            allowed_extensions=VIDEO_EXTENSIONS,
            require_existing_media=require_existing_media,
        )

    for index, hook in enumerate(recipe.get("hooks", []) or []):
        hook_path = hook.get("hook_video_path") or hook.get("path") or hook.get("video_path")
        if hook_path and str(hook_path).strip():
            resolve_recipe_media_path(
                hook_path,
                field_name=f"hooks[{index}].hook_video_path",
                allowed_extensions=VIDEO_EXTENSIONS,
                require_existing_media=require_existing_media,
            )

    watermark = recipe.get("watermark", {}) or {}
    if str(watermark.get("image_path", "")).strip():
        resolve_recipe_media_path(
            watermark["image_path"],
            field_name="watermark.image_path",
            allowed_extensions=IMAGE_EXTENSIONS,
            require_existing_media=require_existing_media,
        )


def normalize_recipe_media_paths(recipe: dict[str, Any], *, require_existing_media: bool = False) -> dict[str, Any]:
    normalized = deepcopy(recipe)
    captions = normalized.get("captions", {})
    if captions.get("enabled") and str(captions.get("burned_srt_path", "")).strip():
        captions["burned_srt_path"] = str(
            resolve_recipe_media_path(
                captions["burned_srt_path"],
                field_name="captions.burned_srt_path",
                allowed_extensions=CAPTION_EXTENSIONS,
                require_existing_media=require_existing_media,
            )
        )
    broll_items = normalized.get("broll", []) or []
    for index, item in enumerate(broll_items):
        item["path"] = str(
            resolve_recipe_media_path(
                item.get("path"),
                field_name=f"broll[{index}].path",
                allowed_extensions=VIDEO_EXTENSIONS,
                require_existing_media=require_existing_media,
            )
        )
    frame = normalized.get("frame", {}) or {}
    if frame.get("enabled") and str(frame.get("logo_path", "")).strip():
        frame["logo_path"] = str(
            resolve_recipe_media_path(
                frame["logo_path"],
                field_name="frame.logo_path",
                allowed_extensions=IMAGE_EXTENSIONS,
                require_existing_media=require_existing_media,
            )
        )
        normalized["frame"] = frame
    audio = normalized.get("audio", {}) or {}
    if str(audio.get("music_path", "")).strip():
        audio["music_path"] = str(
            resolve_recipe_media_path(
                audio["music_path"],
                field_name="audio.music_path",
                allowed_extensions=AUDIO_EXTENSIONS,
                require_existing_media=require_existing_media,
            )
        )
        normalized["audio"] = audio

    split = normalized.get("split", {}) or {}
    if str(split.get("secondary_video_path", "")).strip():
        split["secondary_video_path"] = str(
            resolve_recipe_media_path(
                split["secondary_video_path"],
                field_name="split.secondary_video_path",
                allowed_extensions=VIDEO_EXTENSIONS,
                require_existing_media=require_existing_media,
            )
        )
        normalized["split"] = split

    hooks = normalized.get("hooks", []) or []
    for index, hook in enumerate(hooks):
        hook_path = hook.get("hook_video_path") or hook.get("path") or hook.get("video_path")
        if hook_path and str(hook_path).strip():
            resolved = str(
                resolve_recipe_media_path(
                    hook_path,
                    field_name=f"hooks[{index}].hook_video_path",
                    allowed_extensions=VIDEO_EXTENSIONS,
                    require_existing_media=require_existing_media,
                )
            )
            if "hook_video_path" in hook:
                hook["hook_video_path"] = resolved
            elif "path" in hook:
                hook["path"] = resolved
            elif "video_path" in hook:
                hook["video_path"] = resolved

    watermark = normalized.get("watermark", {}) or {}
    if str(watermark.get("image_path", "")).strip():
        watermark["image_path"] = str(
            resolve_recipe_media_path(
                watermark["image_path"],
                field_name="watermark.image_path",
                allowed_extensions=IMAGE_EXTENSIONS,
                require_existing_media=require_existing_media,
            )
        )
        normalized["watermark"] = watermark

    return normalized


def resolve_fontfile() -> str | None:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    return next((candidate for candidate in candidates if Path(candidate).exists()), None)


def escape_drawtext(text: str) -> str:
    if not text:
        return ""
    # 1. Normaliza finais de linha (CRLF / CR -> LF)
    cleaned = str(text).replace("\r\n", "\n").replace("\r", "\n")
    # 2. Escapa barras invertidas literais
    cleaned = cleaned.replace("\\", "\\\\")
    # 3. Escapa aspas simples
    cleaned = cleaned.replace("'", "\\'")
    # 4. Escapa dois-pontos
    cleaned = cleaned.replace(":", "\\:")
    # 5. Escapa porcentagem com dupla barra: \\% vira \% no parser, evitando crash de macro no drawtext
    cleaned = cleaned.replace("%", "\\\\%")
    # 6. Escapa virgulas e ponto-e-virgula
    cleaned = cleaned.replace(",", "\\,").replace(";", "\\;")
    # 7. Converte quebras de linha em \\n para o graphparser entregar \n ao drawtext
    cleaned = cleaned.replace("\n", "\\\\n")
    return cleaned


def escape_filter_path(path: str) -> str:
    return path.replace("\\", "/").replace("'", "'\\''").replace(":", "\\:")


RGBA_REGEX = re.compile(
    r"^rgba?\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})(?:\s*,\s*([\d.]+))?\s*\)$",
    re.IGNORECASE,
)


def ffmpeg_color(value: Any, fallback: str = "white") -> str:
    raw = str(value or fallback).strip()
    if not raw:
        return fallback

    # 1. Trata formato funcional rgba(r, g, b, a) ou rgb(r, g, b)
    match = RGBA_REGEX.match(raw)
    if match:
        r, g, b = (max(0, min(255, int(v))) for v in match.group(1, 2, 3))
        a_str = match.group(4)
        if a_str is not None:
            try:
                a_val = float(a_str)
                alpha_byte = round(a_val * 255) if a_val <= 1.0 else round(a_val)
                alpha_byte = max(0, min(255, alpha_byte))
                return f"0x{r:02x}{g:02x}{b:02x}{alpha_byte:02x}"
            except ValueError:
                return f"0x{r:02x}{g:02x}{b:02x}"
        return f"0x{r:02x}{g:02x}{b:02x}"

    # 2. Trata formatos hexadecimais (#RGB, #RGBA, #RRGGBB, #RRGGBBAA)
    if raw.startswith("#"):
        hex_part = raw[1:].strip()
        if hex_part and all(ch in "0123456789abcdefABCDEF" for ch in hex_part):
            if len(hex_part) == 3:  # #RGB -> 0xRRGGBB
                r, g, b = hex_part
                return f"0x{r}{r}{g}{g}{b}{b}".lower()
            if len(hex_part) == 4:  # #RGBA -> 0xRRGGBBAA
                r, g, b, a = hex_part
                return f"0x{r}{r}{g}{g}{b}{b}{a}{a}".lower()
            if len(hex_part) in (6, 8):  # #RRGGBB ou #RRGGBBAA -> 0x...
                return f"0x{hex_part}".lower()

    # 3. Trata formato já com prefixo 0x
    if raw.lower().startswith("0x"):
        hex_part = raw[2:].strip()
        if len(hex_part) in (6, 8) and all(ch in "0123456789abcdefABCDEF" for ch in hex_part):
            return f"0x{hex_part}".lower()

    # 4. Trata nomes de cores e sintaxe de alfa do FFmpeg (ex: 'white', 'white@0.82')
    allowed = "".join(ch for ch in raw if ch.isalnum() or ch in {"@", ".", "_"}).strip()
    if allowed:
        return allowed

    return fallback



def clamped_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))


def has_audio_stream(path: Path) -> bool:
    if not path.exists():
        return True
    try:
        ensure_ffmpeg()
        result = subprocess.run(
            [
                "ffprobe",
                "-hide_banner",
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=index",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        if result.returncode != 0:
            return False
        payload = json.loads(result.stdout or "{}")
        return bool(payload.get("streams"))
    except Exception:
        return True


def drawtext_filter(
    *,
    text: str,
    x: str = "(w-text_w)/2",
    y: str,
    font_size: int,
    font_color: str,
    border_color: str,
    border_width: int,
) -> str:
    fontfile = resolve_fontfile()
    parts = [
        "drawtext",
        f"text='{escape_drawtext(text)}'",
        f"x={x}",
        f"y={y}",
        f"fontsize={font_size}",
        f"fontcolor={ffmpeg_color(font_color, 'white')}",
        f"bordercolor={ffmpeg_color(border_color, 'black')}",
        f"borderw={border_width}",
        "shadowx=2",
        "shadowy=2",
    ]
    if fontfile:
        parts.insert(1, f"fontfile='{escape_filter_path(fontfile)}'")
    return f"drawtext={':'.join(parts[1:])}"


def video_fit_filters(width: int, height: int, fit: str) -> list[str]:
    if fit == "contain":
        return [
            f"scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2",
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
        ]
    if fit == "blur_pad":
        return [
            f"scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2",
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:#121212",
        ]
    return [
        f"scale={width}:{height}:force_original_aspect_ratio=increase:force_divisible_by=2",
        f"crop={width}:{height}",
    ]


def base_video_filters(width: int, height: int, fit: str, fps: Any = None) -> list[str]:
    filters = video_fit_filters(width, height, fit)
    if fps:
        filters.append(f"fps={float(fps):g}")
    return filters


def build_dynamic_zoom_filter(width: int, height: int, effects: dict[str, Any]) -> str | None:
    if not effects.get("dynamic_zoom"):
        return None
    zoom_factor = max(1.05, min(1.35, float(effects.get("zoom_factor", 1.15))))
    interval = max(1.5, min(10.0, float(effects.get("zoom_interval", 4.0))))
    w_crop = f"if(mod(floor(t/{interval:g}),2),{int(width / zoom_factor)},{width})"
    h_crop = f"if(mod(floor(t/{interval:g}),2),{int(height / zoom_factor)},{height})"
    return f"crop=w='{w_crop}':h='{h_crop}':x='(iw-ow)/2':y='0.35*(ih-oh)',scale={width}:{height}:force_divisible_by=2"


def build_video_filters(recipe: dict[str, Any], *, variation_index: int = 1) -> str:
    recipe = normalize_recipe_media_paths(recipe, require_existing_media=True)
    validate_recipe(recipe, require_existing_media=True)
    fmt = recipe.get("format", {})
    width = int(fmt.get("width", 1080))
    height = int(fmt.get("height", 1920))
    resolution_scale = height / 1920
    fit = fmt.get("fit", "crop")
    filters = video_fit_filters(width, height, fit)
    if fmt.get("fps"):
        filters.append(f"fps={float(fmt['fps']):g}")

    # Dynamic Zoom (punch-in inteligente ancorado a 35% Y da linha dos olhos)
    effects = recipe.get("effects", {}) or {}
    zoom_flt = build_dynamic_zoom_filter(width, height, effects)
    if zoom_flt:
        filters.append(zoom_flt)


    text = recipe.get("text", {})
    captions = recipe.get("captions", {})
    font_size = int(text.get("font_size", 74))
    font_color = ffmpeg_color(text.get("font_color", "white"), "white")
    border_color = ffmpeg_color(text.get("border_color", "black"), "black")
    border_width = int(text.get("border_width", 6))

    top = str(text.get("top", "")).strip()
    bottom = str(text.get("bottom", "")).strip()
    if variation_index > 1 and top:
        top = f"{top} #{variation_index}"
    if top:
        filters.append(
            drawtext_filter(
                text=top,
                y=str(round(110 * resolution_scale)),
                font_size=font_size,
                font_color=font_color,
                border_color=border_color,
                border_width=border_width,
            )
        )
    if bottom:
        bottom_margin = round(height * 0.28) if captions.get("enabled") else round(170 * resolution_scale)
        filters.append(
            drawtext_filter(
                text=bottom,
                y=f"h-text_h-{bottom_margin}",
                font_size=max(48, int(font_size * 0.78)),
                font_color=font_color,
                border_color=border_color,
                border_width=border_width,
            )
        )

    # CTAs Dinâmicos em 3 Momentos (Hook 0-3s, Mid-roll, End CTA)
    ctas = recipe.get("ctas", []) or []
    for cta in ctas:
        cta_text = str(cta.get("text", "")).strip()
        if not cta_text:
            continue
        cta_start = float(cta.get("start", 0.0))
        cta_end = float(cta.get("end", cta_start + 3.0))
        cta_pos = str(cta.get("position", "bottom")).lower()
        cta_y = (
            str(round(180 * resolution_scale))
            if cta_pos == "top"
            else f"h-text_h-{round(height * 0.22 if captions.get('enabled') else 220 * resolution_scale)}"
        )
        filters.append(
            drawtext_filter(
                text=cta_text,
                y=cta_y,
                font_size=max(36, round(48 * resolution_scale)),
                font_color=cta.get("font_color", "yellow"),
                border_color=cta.get("border_color", "black"),
                border_width=max(3, round(5 * resolution_scale)),
            )
            + f":enable='between(t,{cta_start:g},{cta_end:g})'"
        )

    if captions.get("enabled"):
        if captions.get("burned_ass_path"):
            filters.append(f"ass='{escape_filter_path(str(captions['burned_ass_path']))}'")
        elif captions.get("burned_srt_path"):
            sub_path = str(captions['burned_srt_path'])
            if sub_path.lower().endswith(('.ass', '.ssa')):
                filters.append(f"ass='{escape_filter_path(sub_path)}'")
            else:
                filters.append(f"subtitles='{escape_filter_path(sub_path)}'")

    watermark = recipe.get("watermark", {})
    if watermark.get("enabled") and watermark.get("text"):
        watermark_margin_x = round(52 * resolution_scale)
        watermark_margin_y = round(56 * resolution_scale)
        filters.append(
            drawtext_filter(
                text=str(watermark["text"]),
                x=f"w-text_w-{watermark_margin_x}",
                y=f"h-text_h-{watermark_margin_y}",
                font_size=max(20, round(34 * resolution_scale)),
                font_color="white@0.82",
                border_color="black@0.75",
                border_width=max(2, round(3 * resolution_scale)),
            )
        )

    filters.append("setsar=1")
    return ",".join(filters)



def frame_enabled(recipe: dict[str, Any]) -> bool:
    return bool((recipe.get("frame", {}) or {}).get("enabled"))


def recipe_music_path(recipe: dict[str, Any]) -> str:
    return str((recipe.get("audio", {}) or {}).get("music_path", "")).strip()


def frame_layout(recipe: dict[str, Any]) -> dict[str, int]:
    fmt = recipe.get("format", {})
    frame = recipe.get("frame", {}) or {}
    width = int(fmt.get("width", 1080))
    height = int(fmt.get("height", 1920))
    header_height = int(frame.get("header_height", max(220, round(height * 0.18))))
    divider_height = int(frame.get("divider_height", max(4, round(height * 0.004))))
    video_margin = int(frame.get("video_margin", 0))

    max_vertical_overhead = height - 120
    if (header_height + divider_height + (video_margin * 2)) > max_vertical_overhead:
        header_height = min(header_height, height - 200)
        video_margin = min(video_margin, 20)

    video_x = max(0, video_margin)
    video_y = header_height + divider_height + video_margin
    video_width = max(16, width - (video_margin * 2))
    layout_mode = recipe.get("layout", "single")
    if layout_mode == "split_vertical":
        video_height = max(16, round((height - video_y - video_margin) / 2))
    else:
        video_height = max(16, height - video_y - video_margin)
    if video_width % 2:
        video_width -= 1
    if video_height % 2:
        video_height -= 1

    raw_logo_size = int(frame.get("logo_size", max(80, round(header_height * 0.48))))
    clamped_logo = max(16, min(header_height, raw_logo_size))
    logo_size = clamped_logo if clamped_logo % 2 == 0 else max(16, clamped_logo - 1)

    max_logo_x = max(0, width - logo_size)
    max_logo_y = max(0, header_height - logo_size)
    logo_x = max(0, min(max_logo_x, int(frame.get("logo_x", max(32, round(width * 0.055))))))
    logo_y = max(0, min(max_logo_y, int(frame.get("logo_y", max(8, round((header_height - logo_size) / 2))))))
    return {
        "width": width,
        "height": height,
        "header_height": header_height,
        "divider_height": divider_height,
        "video_x": video_x,
        "video_y": video_y,
        "video_width": video_width,
        "video_height": video_height,
        "logo_size": logo_size,
        "logo_x": logo_x,
        "logo_y": logo_y,
        "layout_mode": layout_mode,
    }


def append_drawtext_chain(
    chains: list[str],
    *,
    current_label: str,
    output_label: str,
    text: str,
    x: str,
    y: str,
    font_size: int,
    font_color: str,
    border_color: str = "black",
    border_width: int = 0,
) -> str:
    chains.append(
        f"[{current_label}]"
        + drawtext_filter(
            text=text,
            x=x,
            y=y,
            font_size=font_size,
            font_color=font_color,
            border_color=border_color,
            border_width=border_width,
        )
        + f"[{output_label}]"
    )
    return output_label


def append_cta_chains(
    chains: list[str],
    *,
    current_label: str,
    ctas: list[dict[str, Any]],
    height: int,
    resolution_scale: float,
    captions_enabled: bool,
    top_y: str | None = None,
) -> str:
    default_top_y = str(round(180 * resolution_scale))
    bottom_y = f"h-text_h-{round(height * 0.22 if captions_enabled else 220 * resolution_scale)}"
    for idx, cta in enumerate(ctas):
        cta_text = str(cta.get("text", "")).strip()
        if not cta_text:
            continue
        cta_start = float(cta.get("start", 0.0))
        cta_end = float(cta.get("end", cta_start + 3.0))
        cta_pos = str(cta.get("position", "bottom")).lower()
        cta_y = (top_y or default_top_y) if cta_pos == "top" else bottom_y
        output_label = f"vcta{idx + 1}"
        chains.append(
            f"[{current_label}]"
            + drawtext_filter(
                text=cta_text,
                y=cta_y,
                font_size=max(36, round(48 * resolution_scale)),
                font_color=cta.get("font_color", "yellow"),
                border_color=cta.get("border_color", "black"),
                border_width=max(3, round(5 * resolution_scale)),
            )
            + f":enable='between(t,{cta_start:g},{cta_end:g})'[{output_label}]"
        )
        current_label = output_label
    return current_label



def append_broll_overlays(
    chains: list[str],
    *,
    current_label: str,
    broll_items: list[dict[str, Any]],
    first_input_index: int,
    target_width: int,
    target_height: int,
    overlay_x: int,
    overlay_y: int,
) -> str:
    for offset, item in enumerate(broll_items):
        input_index = first_input_index + offset
        opacity = max(0.0, min(1.0, float(item.get("opacity", 1))))
        start = float(item.get("start", 0))
        end = float(item.get("end", start + 5))
        fit = item.get("layout", "cover")
        dur = max(0.1, end - start)
        broll_filters = [f"trim=start=0:duration={dur:g}", f"setpts=PTS-STARTPTS+{start:g}/TB"] + video_fit_filters(target_width, target_height, fit)
        broll_filters.append("format=rgba")
        if opacity < 1:
            broll_filters.append(f"colorchannelmixer=aa={opacity:g}")
        broll_label = f"b{offset + 1}"
        chains.append(f"[{input_index}:v]{','.join(broll_filters)}[{broll_label}]")
        output_label = f"vbroll{offset + 1}"
        enable = f"between(t\\,{start:g}\\,{end:g})"
        chains.append(
            f"[{current_label}][{broll_label}]"
            f"overlay={overlay_x}:{overlay_y}:enable='{enable}'[{output_label}]"
        )
        current_label = output_label
    return current_label


def build_broll_filter_complex(
    recipe: dict[str, Any],
    *,
    variation_index: int = 1,
    first_broll_input_index: int = 1,
) -> str:
    recipe = normalize_recipe_media_paths(recipe, require_existing_media=True)
    fmt = recipe.get("format", {})
    width = int(fmt.get("width", 1080))
    height = int(fmt.get("height", 1920))
    resolution_scale = height / 1920
    base_filters = base_video_filters(width, height, fit=fmt.get("fit", "crop"), fps=fmt.get("fps"))
    effects = recipe.get("effects", {}) or {}
    zoom_flt = build_dynamic_zoom_filter(width, height, effects)
    if zoom_flt:
        base_filters.append(zoom_flt)
    chains = [f"[0:v]{','.join(base_filters)},setsar=1[v_base]"]
    current_label = "v_base"
    broll_items = recipe.get("broll", [])
    if broll_items:
        current_label = append_broll_overlays(
            chains,
            current_label=current_label,
            broll_items=broll_items,
            first_input_index=first_broll_input_index,
            target_width=width,
            target_height=height,
            overlay_x=0,
            overlay_y=0,
        )

    texts = recipe.get("text", {}) or {}
    top = str(texts.get("top", "")).strip()
    bottom = str(texts.get("bottom", "")).strip()
    if variation_index > 1 and top:
        top = f"{top} #{variation_index}"
    font_size = int(texts.get("font_size", 56))
    top_margin = int(texts.get("top_margin", 120))
    bottom_margin = int(texts.get("bottom_margin", 180))
    font_color = ffmpeg_color(texts.get("font_color", "white"), "white")
    border_color = ffmpeg_color(texts.get("border_color", "black"), "black")
    border_width = int(texts.get("border_width", 4))

    if top:
        current_label = append_drawtext_chain(
            chains,
            current_label=current_label,
            output_label="vtoptext",
            text=top,
            x="(w-text_w)/2",
            y=str(top_margin),
            font_size=font_size,
            font_color=font_color,
            border_color=border_color,
            border_width=border_width,
        )
    if bottom:
        current_label = append_drawtext_chain(
            chains,
            current_label=current_label,
            output_label="vbottomtext",
            text=bottom,
            x="(w-text_w)/2",
            y=f"h-text_h-{bottom_margin}",
            font_size=max(48, int(font_size * 0.78)),
            font_color=font_color,
            border_color=border_color,
            border_width=border_width,
        )

    captions = recipe.get("captions", {}) or {}
    ctas = recipe.get("ctas", []) or []
    if ctas:
        current_label = append_cta_chains(
            chains,
            current_label=current_label,
            ctas=ctas,
            height=height,
            resolution_scale=resolution_scale,
            captions_enabled=bool(captions.get("enabled")),
        )

    if captions.get("enabled") and captions.get("burned_srt_path"):
        sub_path_str = str(captions["burned_srt_path"])
        if sub_path_str.lower().endswith(".ass"):
            chains.append(f"[{current_label}]ass='{escape_filter_path(sub_path_str)}'[vcaptions]")
        else:
            chains.append(f"[{current_label}]subtitles='{escape_filter_path(sub_path_str)}'[vcaptions]")
        current_label = "vcaptions"

    watermark = recipe.get("watermark", {}) or {}
    if watermark.get("enabled") and watermark.get("text"):
        watermark_text = str(watermark["text"])
        if "{variation}" in watermark_text:
            watermark_text = watermark_text.replace("{variation}", str(variation_index))
        current_label = append_drawtext_chain(
            chains,
            current_label=current_label,
            output_label="vwatermark",
            text=watermark_text,
            x="w-text_w-48",
            y="h-text_h-56",
            font_size=32,
            font_color="white@0.82",
            border_color="black@0.75",
            border_width=2,
        )

    if current_label != "vout":
        chains.append(f"[{current_label}]null[vout]")
    return ";".join(chains)



def build_framed_filter_complex(
    recipe: dict[str, Any],
    *,
    variation_index: int = 1,
    logo_input_index: int | None = None,
    first_broll_input_index: int = 1,
) -> str:
    recipe = normalize_recipe_media_paths(recipe, require_existing_media=True)
    validate_recipe(recipe, require_existing_media=True)
    fmt = recipe.get("format", {})
    frame = recipe.get("frame", {}) or {}
    layout = frame_layout(recipe)
    width = layout["width"]
    height = layout["height"]
    resolution_scale = height / 1920
    fps = fmt.get("fps", 30)
    video_fit = frame.get("video_fit", fmt.get("fit", "crop"))
    background_color = ffmpeg_color(frame.get("background_color", "white"), "white")
    header_color = ffmpeg_color(frame.get("header_background_color", background_color), background_color)
    divider_color = ffmpeg_color(frame.get("divider_color", "#e02424"), "red")

    effects = recipe.get("effects", {}) or {}
    zoom_flt = build_dynamic_zoom_filter(layout["video_width"], layout["video_height"], effects)
    main_filters = base_video_filters(layout["video_width"], layout["video_height"], video_fit, fps)
    if zoom_flt:
        main_filters.append(zoom_flt)
    chains = [
        f"color=c={background_color}:s={width}x{height}:r={float(fps):g}[base0]",
        f"[base0]drawbox=x=0:y=0:w={width}:h={layout['header_height']}:color={header_color}:t=fill[base1]",
        f"[base1]drawbox=x=0:y={layout['header_height']}:w={width}:h={layout['divider_height']}:color={divider_color}:t=fill[base2]",
        (
            f"[0:v]{','.join(main_filters)},"
            "setsar=1[mainv]"
        ),
        f"[base2][mainv]overlay={layout['video_x']}:{layout['video_y']}:shortest=1[vframe0]",
    ]
    current_label = "vframe0"

    broll_items = recipe.get("broll", []) or []
    if broll_items:
        current_label = append_broll_overlays(
            chains,
            current_label=current_label,
            broll_items=broll_items,
            first_input_index=first_broll_input_index,
            target_width=layout["video_width"],
            target_height=layout["video_height"],
            overlay_x=layout["video_x"],
            overlay_y=layout["video_y"],
        )

    if logo_input_index is not None:
        logo_size = layout["logo_size"]
        chains.append(
            f"[{logo_input_index}:v]"
            f"scale={logo_size}:{logo_size}:force_original_aspect_ratio=decrease:force_divisible_by=2,"
            f"pad={logo_size}:{logo_size}:(ow-iw)/2:(oh-ih)/2:color={header_color},setsar=1[logo]"
        )
        chains.append(
            f"[{current_label}][logo]overlay={layout['logo_x']}:{layout['logo_y']}:shortest=1[vlogo]"
        )
        current_label = "vlogo"

    channel_name = str(frame.get("channel_name", "")).strip()
    if channel_name:
        name_x = int(frame.get("channel_x", layout["logo_x"] + (layout["logo_size"] if logo_input_index is not None else 0) + 48))
        channel_size = int(frame.get("channel_font_size", max(48, round(layout["header_height"] * 0.22))))
        current_label = append_drawtext_chain(
            chains,
            current_label=current_label,
            output_label="vchannel",
            text=channel_name,
            x=str(name_x),
            y=f"({layout['header_height']}-text_h)/2",
            font_size=channel_size,
            font_color=ffmpeg_color(frame.get("channel_color", "#111111"), "black"),
            border_color=ffmpeg_color(frame.get("channel_border_color", "white@0"), "white@0"),
            border_width=int(frame.get("channel_border_width", 0)),
        )

    text = recipe.get("text", {}) or {}
    captions = recipe.get("captions", {}) or {}
    font_size = int(text.get("font_size", 74))
    font_color = ffmpeg_color(text.get("font_color", "white"), "white")
    border_color = ffmpeg_color(text.get("border_color", "black"), "black")
    border_width = int(text.get("border_width", 6))
    top = str(text.get("top", "")).strip()
    bottom = str(text.get("bottom", "")).strip()
    if variation_index > 1 and top:
        top = f"{top} #{variation_index}"
    if top:
        current_label = append_drawtext_chain(
            chains,
            current_label=current_label,
            output_label="vtoptext",
            text=top,
            x="(w-text_w)/2",
            y=str(layout["video_y"] + max(44, round(height * 0.035))),
            font_size=font_size,
            font_color=font_color,
            border_color=border_color,
            border_width=border_width,
        )
    if bottom:
        bottom_margin = round(height * 0.28) if captions.get("enabled") else round(170 * resolution_scale)
        current_label = append_drawtext_chain(
            chains,
            current_label=current_label,
            output_label="vbottomtext",
            text=bottom,
            x="(w-text_w)/2",
            y=f"h-text_h-{bottom_margin}",
            font_size=max(48, int(font_size * 0.78)),
            font_color=font_color,
            border_color=border_color,
            border_width=border_width,
        )

    ctas = recipe.get("ctas", []) or []
    if ctas:
        current_label = append_cta_chains(
            chains,
            current_label=current_label,
            ctas=ctas,
            height=height,
            resolution_scale=resolution_scale,
            captions_enabled=bool(captions.get("enabled")),
            top_y=str(layout["video_y"] + max(44, round(height * 0.035))),
        )


    if captions.get("enabled") and captions.get("burned_srt_path"):
        sub_path_str = str(captions["burned_srt_path"])
        if sub_path_str.lower().endswith(".ass"):
            chains.append(f"[{current_label}]ass='{escape_filter_path(sub_path_str)}'[vcaptions]")
        else:
            chains.append(f"[{current_label}]subtitles='{escape_filter_path(sub_path_str)}'[vcaptions]")
        current_label = "vcaptions"

    watermark = recipe.get("watermark", {}) or {}
    if watermark.get("enabled") and watermark.get("text"):
        watermark_margin_x = round(52 * resolution_scale)
        watermark_margin_y = round(56 * resolution_scale)
        current_label = append_drawtext_chain(
            chains,
            current_label=current_label,
            output_label="vwatermark",
            text=str(watermark["text"]),
            x=f"w-text_w-{watermark_margin_x}",
            y=f"h-text_h-{watermark_margin_y}",
            font_size=max(20, round(34 * resolution_scale)),
            font_color="white@0.82",
            border_color="black@0.75",
            border_width=max(2, round(3 * resolution_scale)),
        )

    if current_label != "vout":
        chains.append(f"[{current_label}]null[vout]")
    return ";".join(chains)


def build_music_audio_filter_complex(
    recipe: dict[str, Any],
    *,
    music_input_index: int,
    input_has_audio: bool = True,
) -> str:
    audio = recipe.get("audio", {}) or {}
    music_volume = clamped_float(audio.get("music_volume", 0.22), 0.22, 0.0, 2.0)
    original_volume = clamped_float(audio.get("original_volume", 1.0), 1.0, 0.0, 2.0)
    preserve_audio = audio.get("preserve", True)
    fade_in = clamped_float(audio.get("fade_in", 0.0), 0.0, 0.0, 10.0)

    music_filters: list[str] = []
    if fade_in > 0:
        music_filters.append(f"afade=t=in:ss=0:d={fade_in:g}")
    music_filters.append(f"volume={music_volume:g}")
    music_filter_str = ",".join(music_filters)

    chains: list[str] = []
    if preserve_audio and input_has_audio:
        voice_clarity = audio.get("voice_clarity", {}) or {}
        voice_filter_str = f"volume={original_volume:g}"
        if voice_clarity.get("enabled"):
            from .audio_lab import build_vocal_clarity_filter
            voice_filter_str += f",{build_vocal_clarity_filter(voice_clarity)}"

        chains.append(f"[0:a]{voice_filter_str},aformat=channel_layouts=stereo:sample_rates=48000[a0]")
        chains.append(f"[{music_input_index}:a]{music_filter_str},aformat=channel_layouts=stereo:sample_rates=48000[m0]")

        ducking = audio.get("ducking", {}) or {}
        if ducking.get("enabled"):
            th = clamped_float(ducking.get("threshold", 0.06), 0.06, 0.001, 1.0)
            rt = clamped_float(ducking.get("ratio", 6.0), 6.0, 1.0, 20.0)
            att = int(clamped_float(ducking.get("attack_ms", 30), 30.0, 1.0, 2000.0))
            rel = int(clamped_float(ducking.get("release_ms", 450), 450.0, 10.0, 5000.0))
            chains.append("[a0]asplit=2[a_voice][a_trigger]")
            chains.append(f"[m0][a_trigger]sidechaincompress=threshold={th:.3f}:ratio={rt:.1f}:attack={att}:release={rel}:knee=3[m_duck]")
            chains.append("[a_voice][m_duck]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[a_mix]")
        else:
            chains.append("[a0][m0]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[a_mix]")
    else:
        chains.append(f"[{music_input_index}:a]{music_filter_str},aformat=channel_layouts=stereo:sample_rates=48000[a_mix]")
    if audio.get("normalize", True):
        chains.append("[a_mix]loudnorm=I=-14:TP=-1.5:LRA=11[aout]")
    else:
        chains.append("[a_mix]anull[aout]")
    return ";".join(chains)


def build_ffmpeg_command(
    *,
    input_path: Path,
    output_path: Path,
    recipe: dict[str, Any],
    variation_index: int = 1,
    input_has_audio: bool = True,
) -> list[str]:
    ensure_ffmpeg()
    recipe = normalize_recipe_media_paths(recipe, require_existing_media=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    trim = recipe.get("trim", {})
    audio = recipe.get("audio", {})
    export = recipe.get("export", {})
    command = ["ffmpeg", "-hide_banner", "-nostdin", "-y"]
    start = trim.get("start")
    if start not in (None, "", 0, 0.0):
        command += ["-ss", str(start)]
    command += ["-i", str(input_path)]
    logo_input_index: int | None = None
    frame = recipe.get("frame", {}) or {}
    if frame_enabled(recipe) and str(frame.get("logo_path", "")).strip():
        logo_input_index = 1
        command += ["-loop", "1", "-i", str(frame["logo_path"])]
    broll_items = recipe.get("broll", [])
    first_broll_input_index = 1 + (1 if logo_input_index is not None else 0)
    for item in broll_items:
        broll_path = str(item.get("path", "")).strip()
        if broll_path:
            command += ["-stream_loop", "-1", "-i", broll_path]
    music_path = recipe_music_path(recipe)
    music_input_index = first_broll_input_index + len(broll_items)
    if music_path:
        command += ["-stream_loop", "-1", "-i", music_path]
    end = trim.get("end")
    if end not in (None, ""):
        if start not in (None, ""):
            command += ["-t", str(float(end) - float(start or 0))]
        else:
            command += ["-to", str(end)]
    preserve_audio = audio.get("preserve", True)

    complex_filters: list[str] = []
    has_video_complex = frame_enabled(recipe) or bool(broll_items)
    if frame_enabled(recipe):
        complex_filters.append(
            build_framed_filter_complex(
                recipe,
                variation_index=variation_index,
                logo_input_index=logo_input_index,
                first_broll_input_index=first_broll_input_index,
            )
        )
    elif broll_items:
        complex_filters.append(
            build_broll_filter_complex(
                recipe,
                variation_index=variation_index,
                first_broll_input_index=first_broll_input_index,
            )
        )
    if music_path:
        complex_filters.append(
            build_music_audio_filter_complex(
                recipe,
                music_input_index=music_input_index,
                input_has_audio=input_has_audio,
            )
        )
    if complex_filters:
        command += ["-filter_complex", ";".join(complex_filters)]

    if has_video_complex:
        command += ["-map", "[vout]"]
    else:
        command += ["-map", "0:v:0"]
    if music_path:
        command += ["-map", "[aout]"]
    elif preserve_audio:
        command += ["-map", "0:a?"]
    command += ["-sn", "-dn"]
    if not has_video_complex:
        command += ["-vf", build_video_filters(recipe, variation_index=variation_index)]
    from .media import resolve_render_codec
    
    configured_codec = export.get("codec", "libx264")
    final_codec, accel = resolve_render_codec(configured_codec)

    if "nvenc" in final_codec:
        crf_val = export.get("crf", 23)
        raw_preset = export.get("preset", "veryfast")
        nvenc_preset = "fast" if raw_preset in {"veryfast", "superfast", "ultrafast"} else "medium" if raw_preset == "medium" else "slow"
        command += [
            "-c:v",
            final_codec,
            "-preset",
            nvenc_preset,
            "-rc:v",
            "constqp",
            "-cq:v",
            str(crf_val),
            "-pix_fmt",
            "yuv420p",
        ]
    elif "qsv" in final_codec:
        crf_val = export.get("crf", 23)
        command += [
            "-c:v",
            final_codec,
            "-global_quality",
            str(crf_val),
            "-pix_fmt",
            "nv12",
        ]
    else:
        command += [
            "-c:v",
            final_codec,
            "-preset",
            export.get("preset", "veryfast"),
            "-crf",
            str(export.get("crf", 23)),
            "-pix_fmt",
            "yuv420p",
        ]
    if music_path or (preserve_audio and input_has_audio):
        if audio.get("normalize", True) and not music_path:
            command += ["-af", "loudnorm=I=-14:TP=-1.5:LRA=11"]
        command += ["-c:a", "aac", "-b:a", "128k", "-ar", "48000"]
    else:
        command += ["-an"]
    if music_path:
        command += ["-shortest"]
    command += ["-movflags", "+faststart", str(output_path)]
    return command


def render_video(
    *,
    input_path: Path,
    output_path: Path,
    thumbnail_path: Path,
    recipe: dict[str, Any],
    variation_index: int = 1,
    should_cancel: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    temp_output_path = output_path.with_name(f"{output_path.stem}.tmp{output_path.suffix}")
    if temp_output_path.exists():
        temp_output_path.unlink()
    if output_path.exists():
        output_path.unlink()

    if should_cancel and should_cancel():
        raise RenderCanceledError("Render cancelado pelo usuario.")
    music_path = recipe_music_path(normalize_recipe_media_paths(recipe, require_existing_media=True))
    input_has_audio = has_audio_stream(input_path)
    command = build_ffmpeg_command(
        input_path=input_path,
        output_path=temp_output_path,
        recipe=recipe,
        variation_index=variation_index,
        input_has_audio=input_has_audio,
    )
    try:
        completed = run_ffmpeg_command(command, should_cancel=should_cancel)
    except subprocess.TimeoutExpired as exc:
        temp_output_path.unlink(missing_ok=True)
        raise RuntimeError(f"FFmpeg excedeu o limite de {RENDER_TIMEOUT_SECONDS}s.") from exc
    except RenderCanceledError:
        temp_output_path.unlink(missing_ok=True)
        raise
    if completed.returncode != 0:
        temp_output_path.unlink(missing_ok=True)
        raise RuntimeError(completed.stderr[-4000:] or "FFmpeg falhou sem stderr.")
    temp_output_path.replace(output_path)
    metadata = ffprobe_metadata(output_path)
    peak_rss_bytes = getattr(completed, "peak_rss_bytes", None)
    if isinstance(peak_rss_bytes, int) and peak_rss_bytes > 0:
        metadata["peak_rss_bytes"] = peak_rss_bytes
    duration = metadata.get("duration_seconds") or 0
    thumbnail_second = min(2.0, max(0.0, duration * 0.25))
    generate_thumbnail(output_path, thumbnail_path, at_seconds=thumbnail_second)
    if should_cancel and should_cancel():
        output_path.unlink(missing_ok=True)
        thumbnail_path.unlink(missing_ok=True)
        raise RenderCanceledError("Render cancelado pelo usuario.")
    return metadata


def copy_recipe_manifest(recipe: dict[str, Any], target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "render-recipe.json").write_text(
        json.dumps(recipe, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
