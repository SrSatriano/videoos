from __future__ import annotations

import json
import os
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("VIDEO_OS_DATA_DIR", APP_ROOT / "data")).resolve()
SETTINGS_FILE = DATA_DIR / "settings.json"
PLANEJAMENTO_DIR = APP_ROOT / "Planejamento"

INCOMING_DIR = DATA_DIR / "incoming"
ASSETS_DIR = DATA_DIR / "assets"
RENDERS_DIR = DATA_DIR / "renders"
THUMBNAILS_DIR = DATA_DIR / "thumbnails"
PUBLISH_PACKAGES_DIR = DATA_DIR / "publish-packages"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
PROXIES_DIR = DATA_DIR / "proxies"
BROLL_DIR = DATA_DIR / "broll"
DB_DIR = DATA_DIR / "db"
LOGS_DIR = DATA_DIR / "logs"

BROLL_DIR.mkdir(parents=True, exist_ok=True)



def _split_path_env(value: str) -> list[Path]:
    return [Path(part.strip()).resolve() for part in value.split(";") if part.strip()]


ALLOWED_OUTPUT_ROOTS = [
    DATA_DIR,
    PLANEJAMENTO_DIR.resolve(),
    *_split_path_env(os.getenv("VIDEO_OS_ALLOWED_OUTPUT_ROOTS", "")),
]

ALLOWED_RECIPE_MEDIA_ROOTS = [
    DATA_DIR,
    PLANEJAMENTO_DIR.resolve(),
    *_split_path_env(os.getenv("VIDEO_OS_ALLOWED_RECIPE_MEDIA_ROOTS", "")),
]


def path_is_within_roots(path: Path, roots: list[Path] | None = None) -> bool:
    resolved = path.resolve()
    for root in roots or ALLOWED_OUTPUT_ROOTS:
        try:
            resolved.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


def resolve_configured_directory(raw_path: str) -> Path | None:
    candidate = Path(raw_path.strip()).resolve()
    return candidate if path_is_within_roots(candidate) else None


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", "")).strip()
GEMINI_MODEL = os.getenv("VIDEO_OS_GEMINI_MODEL", "gemini-2.0-flash").strip()


def load_custom_settings() -> None:
    global INCOMING_DIR, ASSETS_DIR, RENDERS_DIR, THUMBNAILS_DIR, PUBLISH_PACKAGES_DIR, TRANSCRIPTS_DIR, PROXIES_DIR, DB_DIR
    global GOOGLE_API_KEY, GEMINI_MODEL
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "incoming_dir" in data and (path := resolve_configured_directory(data["incoming_dir"])): INCOMING_DIR = path
                if "assets_dir" in data and (path := resolve_configured_directory(data["assets_dir"])): ASSETS_DIR = path
                if "renders_dir" in data and (path := resolve_configured_directory(data["renders_dir"])): RENDERS_DIR = path
                if "thumbnails_dir" in data and (path := resolve_configured_directory(data["thumbnails_dir"])): THUMBNAILS_DIR = path
                if "publish_packages_dir" in data and (path := resolve_configured_directory(data["publish_packages_dir"])): PUBLISH_PACKAGES_DIR = path
                if "transcripts_dir" in data and (path := resolve_configured_directory(data["transcripts_dir"])): TRANSCRIPTS_DIR = path
                if "proxies_dir" in data and (path := resolve_configured_directory(data["proxies_dir"])): PROXIES_DIR = path
                if "db_dir" in data and (path := resolve_configured_directory(data["db_dir"])): DB_DIR = path
                if "google_api_key" in data and isinstance(data["google_api_key"], str):
                    GOOGLE_API_KEY = data["google_api_key"].strip()
                if "gemini_model" in data and isinstance(data["gemini_model"], str) and data["gemini_model"].strip():
                    GEMINI_MODEL = data["gemini_model"].strip()
        except Exception:
            pass

load_custom_settings()

DATABASE_PATH = DB_DIR / "video_os.sqlite3"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
ALLOW_ANY_IMPORT_PATH = os.getenv("VIDEO_OS_ALLOW_ANY_IMPORT_PATH", "0").lower() in {"1", "true", "yes", "sim"}
HOST_DRIVE_MOUNT = Path(os.getenv("VIDEO_OS_HOST_DRIVE_MOUNT", "/host"))

FFPROBE_TIMEOUT_SECONDS = int(os.getenv("VIDEO_OS_FFPROBE_TIMEOUT_SECONDS", "60"))
THUMBNAIL_TIMEOUT_SECONDS = int(os.getenv("VIDEO_OS_THUMBNAIL_TIMEOUT_SECONDS", "60"))
RENDER_TIMEOUT_SECONDS = int(os.getenv("VIDEO_OS_RENDER_TIMEOUT_SECONDS", "1800"))
OLLAMA_URL = os.getenv("VIDEO_OS_OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("VIDEO_OS_OLLAMA_MODEL", "llama3.1")
WHISPER_MODEL = os.getenv("VIDEO_OS_WHISPER_MODEL", "base")


DEFAULT_IMPORT_ROOTS = [
    APP_ROOT / "Planejamento",
    INCOMING_DIR,
]

IMPORT_ROOTS = [
    Path(part).resolve()
    for part in os.getenv(
        "VIDEO_OS_IMPORT_ROOTS",
        ";".join(str(path) for path in DEFAULT_IMPORT_ROOTS),
    ).split(";")
    if part.strip()
]

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "VIDEO_OS_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = "*" not in CORS_ORIGINS


def ensure_data_dirs() -> None:
    for directory in [
        DATA_DIR,
        INCOMING_DIR,
        ASSETS_DIR,
        RENDERS_DIR,
        THUMBNAILS_DIR,
        PUBLISH_PACKAGES_DIR,
        TRANSCRIPTS_DIR,
        PROXIES_DIR,
        DB_DIR,
        LOGS_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)
