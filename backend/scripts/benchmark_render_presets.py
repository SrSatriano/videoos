from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import tempfile
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

from app.services.media import ffprobe_metadata, generate_thumbnail
from app.services.render import build_ffmpeg_command

try:
    import resource
except ImportError:  # Windows host; the official benchmark runtime is Docker/Linux.
    resource = None  # type: ignore[assignment]


PRESETS = (
    {"id": "1080p", "width": 1080, "height": 1920, "crf": 23},
    {"id": "2k", "width": 1440, "height": 2560, "crf": 21},
    {"id": "4k", "width": 2160, "height": 3840, "crf": 19},
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark the VideoOS 1080p, 2K and 4K render presets.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--logo", type=Path)
    parser.add_argument("--music", type=Path)
    parser.add_argument("--captions", type=Path)
    parser.add_argument("--duration", type=float, default=3.0)
    parser.add_argument("--channel-name", default="VIDEO OS LAB")
    return parser.parse_args()


def require_file(path: Path | None, label: str) -> None:
    if path is not None and not path.is_file():
        raise FileNotFoundError(f"{label} nao encontrado: {path}")


def cgroup_memory_limit_bytes() -> int | None:
    path = Path("/sys/fs/cgroup/memory.max")
    if not path.is_file():
        return None
    value = path.read_text(encoding="utf-8").strip()
    return None if value == "max" else int(value)


def process_rss_bytes(pid: int) -> int:
    status_path = Path(f"/proc/{pid}/status")
    try:
        for line in status_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    except (FileNotFoundError, ProcessLookupError):
        return 0
    return 0


def ffmpeg_version() -> str:
    completed = subprocess.run(
        ["ffmpeg", "-version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        check=True,
    )
    return completed.stdout.splitlines()[0]


def stream_codecs(path: Path) -> dict[str, str | None]:
    completed = subprocess.run(
        [
            "ffprobe",
            "-hide_banner",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,codec_name",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=True,
    )
    streams = json.loads(completed.stdout or "{}").get("streams", [])
    video = next((item.get("codec_name") for item in streams if item.get("codec_type") == "video"), None)
    audio = next((item.get("codec_name") for item in streams if item.get("codec_type") == "audio"), None)
    return {"video_codec": video, "audio_codec": audio}


def base_recipe(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "format": {"width": 1080, "height": 1920, "fit": "crop", "fps": 30},
        "trim": {"start": 0, "end": args.duration},
        "text": {
            "top": "Benchmark de resolucao",
            "bottom": "Mesmo video, mesma receita",
            "font_size": 74,
            "font_color": "white",
            "border_color": "black",
            "border_width": 6,
        },
        "captions": {
            "enabled": args.captions is not None,
            "burned_srt_path": str(args.captions or ""),
        },
        "broll": [],
        "watermark": {"enabled": True, "text": "@videoos", "position": "bottom_right"},
        "frame": {
            "enabled": True,
            "background_color": "white",
            "header_background_color": "white",
            "divider_color": "#e02424",
            "divider_height": 8,
            "header_height": 340,
            "video_margin": 0,
            "video_fit": "crop",
            "logo_path": str(args.logo or ""),
            "logo_size": 164,
            "channel_name": args.channel_name,
            "channel_color": "#111111",
            "channel_font_size": 72,
        },
        "audio": {
            "preserve": True,
            "normalize": True,
            "music_path": str(args.music or ""),
            "music_volume": 0.22,
            "original_volume": 1.0,
        },
        "export": {"codec": "libx264", "crf": 23, "preset": "veryfast"},
    }


def recipe_for_preset(base: dict[str, Any], preset: dict[str, Any]) -> dict[str, Any]:
    recipe = deepcopy(base)
    scale = preset["height"] / 1920
    recipe["format"].update(width=preset["width"], height=preset["height"])
    recipe["text"].update(
        font_size=round(74 * scale),
        border_width=max(2, round(6 * scale)),
    )
    recipe["frame"].update(
        header_height=round(340 * scale),
        divider_height=max(6, round(8 * scale)),
        logo_size=round((164 * scale) / 2) * 2,
        channel_font_size=round(72 * scale),
    )
    recipe["export"]["crf"] = preset["crf"]
    return recipe


def run_ffmpeg(command: list[str]) -> dict[str, float | int | None]:
    before = resource.getrusage(resource.RUSAGE_CHILDREN) if resource else None
    started = time.perf_counter()
    peak_rss = 0
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as stderr:
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=stderr, text=True)
        while process.poll() is None:
            peak_rss = max(peak_rss, process_rss_bytes(process.pid))
            time.sleep(0.1)
        peak_rss = max(peak_rss, process_rss_bytes(process.pid))
        elapsed = time.perf_counter() - started
        after = resource.getrusage(resource.RUSAGE_CHILDREN) if resource else None
        stderr.seek(0)
        error_text = stderr.read()
    if process.returncode != 0:
        raise RuntimeError(error_text[-4000:] or f"FFmpeg terminou com codigo {process.returncode}.")
    cpu_seconds = None
    if before is not None and after is not None:
        cpu_seconds = (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime)
    return {
        "wall_seconds": round(elapsed, 3),
        "cpu_seconds": round(cpu_seconds, 3) if cpu_seconds is not None else None,
        "average_cpu_percent": round((cpu_seconds / elapsed) * 100, 1) if cpu_seconds is not None and elapsed else None,
        "peak_rss_bytes": peak_rss,
    }


def render_preset(args: argparse.Namespace, base: dict[str, Any], preset: dict[str, Any]) -> dict[str, Any]:
    recipe = recipe_for_preset(base, preset)
    output_path = args.output_root / f"benchmark-{preset['id']}.mp4"
    temp_path = output_path.with_name(f"{output_path.stem}.tmp{output_path.suffix}")
    thumbnail_path = args.output_root / f"benchmark-{preset['id']}.jpg"
    temp_path.unlink(missing_ok=True)
    output_path.unlink(missing_ok=True)
    command = build_ffmpeg_command(
        input_path=args.input,
        output_path=temp_path,
        recipe=recipe,
        variation_index=1,
        input_has_audio=True,
    )
    try:
        process_metrics = run_ffmpeg(command)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    temp_path.replace(output_path)
    metadata = ffprobe_metadata(output_path)
    codecs = stream_codecs(output_path)
    duration = float(metadata.get("duration_seconds") or 0)
    generate_thumbnail(output_path, thumbnail_path, at_seconds=min(1.0, max(0.0, duration * 0.25)))
    size_bytes = output_path.stat().st_size
    bitrate = round((size_bytes * 8) / duration) if duration else 0
    return {
        "preset": preset["id"],
        "width": metadata.get("width"),
        "height": metadata.get("height"),
        "duration_seconds": duration,
        **codecs,
        "fps": metadata.get("fps"),
        "size_bytes": size_bytes,
        "average_bitrate_bps": bitrate,
        "realtime_factor": round(duration / float(process_metrics["wall_seconds"]), 3),
        "output_path": str(output_path),
        "thumbnail_path": str(thumbnail_path),
        "recipe": recipe,
        **process_metrics,
    }


def main() -> None:
    args = parse_args()
    require_file(args.input, "Input")
    require_file(args.logo, "Logo")
    require_file(args.music, "Musica")
    require_file(args.captions, "Legenda")
    if args.duration <= 0:
        raise ValueError("duration deve ser maior que zero.")
    args.output_root.mkdir(parents=True, exist_ok=True)

    base = base_recipe(args)
    results = []
    for preset in PRESETS:
        print(f"Renderizando {preset['id']} ({preset['width']}x{preset['height']})...", flush=True)
        result = render_preset(args, base, preset)
        results.append(result)
        print(
            f"{preset['id']}: {result['wall_seconds']}s, "
            f"{result['size_bytes']} bytes, pico RSS {result['peak_rss_bytes']} bytes",
            flush=True,
        )

    report = {
        "benchmark": "videoos-resolution-presets/v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "input_path": str(args.input),
        "duration_requested_seconds": args.duration,
        "ffmpeg": ffmpeg_version(),
        "runtime": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
            "cgroup_memory_limit_bytes": cgroup_memory_limit_bytes(),
        },
        "results": results,
    }
    report_path = args.output_root / "benchmark-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Relatorio: {report_path}", flush=True)


if __name__ == "__main__":
    main()
