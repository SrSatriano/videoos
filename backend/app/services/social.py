from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from ..config import INCOMING_DIR, path_is_within_roots
from ..database import SessionLocal
from ..models import DownloadJob, now_utc
from .audit import record_event
from .media import import_paths, resolve_user_path, safe_upload_name


URL_RE = re.compile(r"^https?://", re.IGNORECASE)
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
GALLERYDL_TIMEOUT_SECONDS = 900
INSTAGRAM_PROFILE_COOKIES_REQUIRED = (
    "Para baixar um perfil inteiro do Instagram e preciso enviar cookies de uma sessao autorizada "
    "(arquivo cookies.txt ou importacao do navegador). Perfis publicos exigem login para listar os videos. "
    "Sem cookies, use URLs diretas de Reels/posts."
)
SUPPORTED_BROWSER_COOKIE_SOURCES = {"chrome", "edge", "firefox", "brave", "chromium", "opera", "vivaldi"}
# Ordem importa: markers mais especificos (edge/brave) antes de "chrome".
DEFAULT_BROWSER_PROGID_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("edge", ("msedge", "edge")),
    ("brave", ("brave",)),
    ("opera", ("opera",)),
    ("vivaldi", ("vivaldi",)),
    ("firefox", ("firefox",)),
    ("chromium", ("chromium",)),
    ("chrome", ("chrome",)),
)
COOKIE_FILE_EXTENSIONS = {".txt", ".cookies"}
MAX_COOKIE_FILE_BYTES = 2 * 1024 * 1024
COOKIE_FILE_HELP = (
    "No Docker, importe cookies com um arquivo cookies.txt (formato Netscape) ou um export JSON "
    "de extensao de cookies (Cookie-Editor / Get cookies.txt) - a conversao e automatica. "
    "Nao cole os cookies manualmente em um txt: exporte pela extensao para preservar o formato. "
    "A importacao direta do navegador do Windows nao fica disponivel dentro do container."
)
INSTAGRAM_PROFILE_HELP = (
    "Perfis do Instagram sao instaveis no yt-dlp. Para maior confiabilidade, use cookies.txt "
    "de uma sessao autorizada e cole URLs diretas de Reels/posts publicos ou autorizados."
)
INSTAGRAM_EXTRACTOR_HELP = (
    "O extractor de perfil do Instagram falhou nesta versao do yt-dlp. Atualize/reconstrua "
    "o ambiente, use cookies.txt e, se persistir, cole URLs diretas de Reels/posts autorizados."
)
INSTAGRAM_NON_PROFILE_PATHS = {
    "accounts",
    "direct",
    "explore",
    "p",
    "reel",
    "reels",
    "stories",
    "tv",
}
INSTAGRAM_PROFILE_TAB_PATHS = {
    "guides",
    "reels",
    "tagged",
}
INSTAGRAM_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.]+$")
INSTAGRAM_PROFILE_RE = re.compile(
    r"^https?://(?:www\.)?instagram\.com/([A-Za-z0-9_.]+)/?(?:[?#].*)?$",
    re.IGNORECASE,
)
INSTAGRAM_EXTRACTOR_FAILURE_MARKERS = (
    "functionality for this site has been marked as broken",
    "[instagram:user]",
    "unable to extract data",
)


def cookies_upload_dir() -> Path:
    return INCOMING_DIR / "massloader-cookies"


def is_container_runtime() -> bool:
    forced = os.getenv("VIDEO_OS_FORCE_CONTAINER_RUNTIME", "").lower() in {"1", "true", "yes", "sim"}
    return forced or Path("/.dockerenv").exists() or Path("/run/.containerenv").exists()


def browser_cookie_import_supported() -> bool:
    return not is_container_runtime()


def detect_default_browser() -> str | None:
    """Identifica o navegador padrao do Windows via registro e mapeia para um nome
    aceito por yt-dlp/gallery-dl. Retorna None fora do Windows ou se nao reconhecer."""
    if sys.platform != "win32":
        return None
    try:
        import winreg
    except Exception:  # noqa: BLE001
        return None
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice",
        ) as key:
            prog_id, _ = winreg.QueryValueEx(key, "ProgId")
    except OSError:
        return None
    prog_id_lower = str(prog_id or "").lower()
    for browser, markers in DEFAULT_BROWSER_PROGID_MARKERS:
        if any(marker in prog_id_lower for marker in markers):
            return browser
    return None


def ytdlp_version() -> str | None:
    try:
        return metadata.version("yt-dlp")
    except metadata.PackageNotFoundError:
        try:
            from yt_dlp.version import __version__
        except Exception:  # noqa: BLE001
            return None
        return __version__


def gallerydl_version() -> str | None:
    try:
        return metadata.version("gallery-dl")
    except metadata.PackageNotFoundError:
        try:
            from gallery_dl.version import __version__
        except Exception:  # noqa: BLE001
            return None
        return __version__


def gallerydl_command() -> list[str] | None:
    exe = shutil.which("gallery-dl")
    if exe:
        return [exe]
    try:
        import gallery_dl  # noqa: F401
    except Exception:  # noqa: BLE001
        return None
    return [sys.executable, "-m", "gallery_dl"]


def instagram_profile_username(source: str) -> str | None:
    match = INSTAGRAM_PROFILE_RE.match(source.strip())
    if not match:
        return None
    username = match.group(1)
    if username.lower() in INSTAGRAM_NON_PROFILE_PATHS:
        return None
    if not INSTAGRAM_USERNAME_RE.match(username):
        return None
    return username


def normalize_browser_cookie_source(raw_value: str | None) -> str | None:
    if not raw_value:
        return None
    browser = raw_value.strip().lower()
    if not browser:
        return None
    if browser not in SUPPORTED_BROWSER_COOKIE_SOURCES:
        raise HTTPException(status_code=422, detail=f"Navegador de cookies nao suportado: {browser}")
    return browser


def resolve_cookie_browser(raw_value: str | None) -> str | None:
    """Como `normalize_browser_cookie_source`, mas aceita o valor especial "auto",
    que detecta o navegador padrao do sistema automaticamente."""
    if raw_value and raw_value.strip().lower() == "auto":
        if not browser_cookie_import_supported():
            raise HTTPException(status_code=422, detail=COOKIE_FILE_HELP)
        detected = detect_default_browser()
        if not detected:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Nao foi possivel identificar o navegador padrao do sistema. "
                    "Selecione o navegador manualmente ou envie um arquivo cookies.txt."
                ),
            )
        return detected
    return normalize_browser_cookie_source(raw_value)


def resolve_cookie_file(raw_path: str) -> Path:
    cleaned = raw_path.strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail="cookies_file_path nao pode ficar vazio.")

    candidate = resolve_user_path(cleaned).resolve()
    allowed_root = cookies_upload_dir().resolve()
    if not path_is_within_roots(candidate, [allowed_root]):
        raise HTTPException(
            status_code=400,
            detail=f"cookies_file_path fora da pasta permitida: {allowed_root}",
        )
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail=f"Arquivo de cookies nao encontrado: {candidate}")
    if candidate.suffix.lower() not in COOKIE_FILE_EXTENSIONS:
        raise HTTPException(status_code=422, detail="Use um arquivo de cookies .txt ou .cookies.")
    return candidate


NETSCAPE_COOKIE_HEADER = "# Netscape HTTP Cookie File\n"
COOKIE_FORMAT_ERROR = (
    "Arquivo de cookies invalido. Esperado o formato Netscape (cookies.txt) ou um export "
    "JSON de extensao de cookies (ex.: Cookie-Editor / Get cookies.txt). Nao cole os cookies "
    "manualmente em um txt: exporte pela extensao para preservar o formato."
)


def _bool_field(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().upper() in {"TRUE", "1", "YES"}
    return bool(value)


def _netscape_line_from_json_cookie(cookie: dict[str, Any]) -> str | None:
    """Converte um cookie no formato JSON (Cookie-Editor/EditThisCookie) em uma linha Netscape."""
    name = cookie.get("name")
    domain = cookie.get("domain")
    if not name or not domain:
        return None

    domain = str(domain)
    host_only = _bool_field(cookie.get("hostOnly", not domain.startswith(".")))
    include_subdomains = "FALSE" if host_only else "TRUE"
    path = str(cookie.get("path") or "/")
    secure = "TRUE" if _bool_field(cookie.get("secure", False)) else "FALSE"

    expiry_raw = cookie.get("expirationDate", cookie.get("expiry", cookie.get("expires", 0)))
    try:
        expiry = int(float(expiry_raw)) if expiry_raw not in (None, "") else 0
    except (TypeError, ValueError):
        expiry = 0

    value = str(cookie.get("value", ""))
    prefix = "#HttpOnly_" if _bool_field(cookie.get("httpOnly", False)) else ""
    return "\t".join([f"{prefix}{domain}", include_subdomains, path, secure, str(expiry), str(name), value])


def _normalize_json_cookies(text: str) -> list[str] | None:
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None

    if isinstance(data, dict):
        # Alguns exports embrulham a lista em {"cookies": [...]}.
        data = data.get("cookies", data)
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return None

    lines = []
    for item in data:
        if isinstance(item, dict):
            line = _netscape_line_from_json_cookie(item)
            if line:
                lines.append(line)
    return lines


def _normalize_netscape_lines(text: str) -> list[str]:
    """Recupera linhas Netscape com campos separados por espacos (colagem manual)."""
    lines = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("#") and not stripped.startswith("#HttpOnly_"):
            continue
        # Divide por qualquer espaco em branco, mantendo o valor (7o campo) intacto.
        fields = stripped.split(maxsplit=6) if "\t" not in stripped else stripped.split("\t")
        if len(fields) == 7:
            lines.append("\t".join(field.strip() for field in fields))
    return lines


def normalize_cookie_content(content: bytes) -> bytes:
    """Converte o conteudo enviado para um cookies.txt Netscape valido.

    Aceita export JSON de extensoes de cookies e recupera arquivos Netscape colados
    manualmente (TAB trocado por espacos). Levanta 422 quando nada aproveitavel e encontrado.
    """
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=422, detail="Arquivo de cookies deve ser texto.") from exc

    lines = _normalize_json_cookies(text)
    if lines is None:
        lines = _normalize_netscape_lines(text)

    if not lines:
        raise HTTPException(status_code=422, detail=COOKIE_FORMAT_ERROR)

    body = NETSCAPE_COOKIE_HEADER + "\n".join(lines) + "\n"
    return body.encode("utf-8")


def store_cookie_upload(filename: str, content: bytes) -> dict[str, Any]:
    if not content:
        raise HTTPException(status_code=422, detail="Arquivo de cookies vazio.")
    if len(content) > MAX_COOKIE_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo de cookies excede 2 MB.")
    if b"\x00" in content:
        raise HTTPException(status_code=422, detail="Arquivo de cookies deve ser texto.")

    safe_name = safe_upload_name(filename or "cookies.txt")
    if Path(safe_name).suffix.lower() not in COOKIE_FILE_EXTENSIONS:
        raise HTTPException(status_code=422, detail="Envie um arquivo .txt ou .cookies.")

    normalized = normalize_cookie_content(content)

    target_dir = cookies_upload_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    target = target_dir / f"{stamp}-{safe_name}"
    counter = 1
    while target.exists():
        target = target_dir / f"{stamp}-{counter}-{safe_name}"
        counter += 1
    target.write_bytes(normalized)
    return {"path": str(target), "filename": target.name, "size_bytes": target.stat().st_size}


def massloader_base_dir() -> Path:
    return INCOMING_DIR / "massloader"


def sanitize_destination_subpath(destination: str) -> str:
    """Transforma o nome de pasta digitado pelo usuario em um subcaminho seguro.

    Aceita nomes simples ("chumai") ou subpastas ("clientes/chumai"). Remove
    componentes perigosos ("..", letras de drive, caracteres invalidos)."""
    cleaned = destination.strip().strip('"').replace("\\", "/")
    parts: list[str] = []
    for raw_part in cleaned.split("/"):
        piece = raw_part.split(":")[-1].strip()  # descarta prefixo de drive tipo "C:"
        if not piece or piece in {".", ".."}:
            continue
        safe = "".join(ch if ch.isalnum() or ch in {"-", "_", ".", " "} else "-" for ch in piece).strip(" .-")
        if safe:
            parts.append(safe)
    return "/".join(parts)


def resolve_download_target_dir(destination: str | None) -> Path | None:
    """Resolve a pasta de destino escolhida pelo usuario dentro da area do massloader.

    Retorna None quando nenhum destino e informado (usa a pasta automatica com timestamp)."""
    if not destination or not destination.strip():
        return None
    subpath = sanitize_destination_subpath(destination)
    if not subpath:
        raise HTTPException(status_code=422, detail="Nome de pasta de destino invalido.")
    base = massloader_base_dir().resolve()
    target = (base / subpath).resolve()
    if not path_is_within_roots(target, [base]):
        raise HTTPException(status_code=422, detail="Pasta de destino fora da area permitida.")
    return target


def massloader_status() -> dict[str, Any]:
    return {
        "configured": bool(shutil.which("yt-dlp")),
        "mode": "hybrid",
        "yt_dlp_version": ytdlp_version(),
        "gallery_dl_version": gallerydl_version(),
        "gallery_dl_configured": gallerydl_command() is not None,
        "profile_downloads": "gallery-dl",
        "profile_requires_cookies": True,
        "default_browser": detect_default_browser() if browser_cookie_import_supported() else None,
        "target_dir": str(INCOMING_DIR / "massloader"),
        "cookies_dir": str(cookies_upload_dir()),
        "cookie_file_upload": True,
        "cookie_file_extensions": sorted(COOKIE_FILE_EXTENSIONS),
        "browser_cookie_import_supported": browser_cookie_import_supported(),
        "cookie_help": COOKIE_FILE_HELP,
        "requires_rights_confirmation": True,
    }


def parse_sources(raw: str) -> list[str]:
    raw_sources = [
        line.strip()
        for line in raw.replace(",", "\n").splitlines()
        if line.strip()
    ]
    sources = []
    for src in raw_sources:
        if src.lower().startswith("www."):
            src = "https://" + src
        sources.append(normalize_instagram_source_url(src))

    if not sources:
        raise HTTPException(status_code=422, detail="Informe pelo menos uma URL.")
    invalid = [source for source in sources if not URL_RE.match(source)]
    if invalid:
        raise HTTPException(status_code=422, detail=f"URL invalida: {invalid[0]}")
    return sources


def normalize_instagram_source_url(source: str) -> str:
    cleaned = source.strip()
    parsed = urlparse(cleaned)
    host = parsed.netloc.lower()
    if host not in {"instagram.com", "www.instagram.com"}:
        return cleaned

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2:
        return cleaned

    username, tab = parts[0], parts[1].lower()
    if tab not in INSTAGRAM_PROFILE_TAB_PATHS:
        return cleaned

    if username.lower() in INSTAGRAM_NON_PROFILE_PATHS or not INSTAGRAM_USERNAME_RE.match(username):
        return cleaned

    return f"https://www.instagram.com/{username}/"


def is_instagram_profile_url(source: str) -> bool:
    match = INSTAGRAM_PROFILE_RE.match(source.strip())
    if not match:
        return False
    first_path = match.group(1).lower()
    return first_path not in INSTAGRAM_NON_PROFILE_PATHS


def normalize_downloader_messages(
    messages: list[str],
    *,
    sources: list[str] | None = None,
    downloaded_count: int = 0,
) -> list[str]:
    normalized: list[str] = []

    def add(message: str) -> None:
        cleaned = message.strip()
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)

    for message in messages:
        add(message)

    combined = " ".join(normalized).lower()
    if any(marker in combined for marker in INSTAGRAM_EXTRACTOR_FAILURE_MARKERS):
        add(INSTAGRAM_EXTRACTOR_HELP)

    if sources and downloaded_count == 0 and any(is_instagram_profile_url(source) for source in sources):
        add(INSTAGRAM_PROFILE_HELP)

    return normalized



class MyLogger:
    def __init__(self):
        self.messages = []

    def debug(self, msg: str) -> None:
        pass

    def info(self, msg: str) -> None:
        pass

    def warning(self, msg: str) -> None:
        self.messages.append(f"WARNING: {msg}")

    def error(self, msg: str) -> None:
        self.messages.append(f"ERROR: {msg}")


def download_with_ytdlp(
    sources: list[str],
    limit: int,
    target_dir: Path,
    cookies_from_browser: str | None = None,
    cookies_file_path: str | None = None,
    offset: int = 0,
    on_file_done: Callable[[int], None] | None = None,
) -> tuple[list[dict[str, str]], list[str]]:
    try:
        from yt_dlp import YoutubeDL
    except ImportError as exc:
        raise HTTPException(
            status_code=501,
            detail="yt-dlp nao esta instalado. Rode o executor para reconstruir o ambiente ou instale backend/requirements.txt.",
        ) from exc

    target_dir.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    logger = MyLogger()
    has_ffmpeg = bool(shutil.which("ffmpeg"))

    done_counter = {"count": 0}

    def _progress_hook(status: dict[str, Any]) -> None:
        if status.get("status") == "finished":
            done_counter["count"] += 1
            if on_file_done:
                on_file_done(done_counter["count"])

    ydl_opts = {
        "outtmpl": str(target_dir / "%(extractor_key)s-%(uploader,channel,uploader_id|unknown)s-%(id)s.%(ext)s"),
        "format": "bv*+ba/best" if has_ffmpeg else "best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "noplaylist": False,
        "playliststart": offset + 1,
        "playlistend": offset + limit,
        "ignoreerrors": True,
        "restrictfilenames": True,
        "retries": 3,
        "fragment_retries": 3,
        "quiet": True,
        "no_warnings": True,
        "logger": logger,
        "progress_hooks": [_progress_hook],
    }

    if not has_ffmpeg:
        errors.append("Aviso: FFmpeg não está disponível no sistema. A qualidade dos downloads poderá ser reduzida para garantir a fusão do áudio e vídeo.")

    if cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = (cookies_from_browser,)

    if cookies_file_path:
        ydl_opts["cookiefile"] = str(resolve_cookie_file(cookies_file_path))

    before = {path.resolve() for path in target_dir.glob("**/*") if path.is_file()}

    try:
        ydl_ctx = YoutubeDL(ydl_opts)
    except Exception as exc:
        if cookies_from_browser or cookies_file_path:
            raise HTTPException(status_code=422, detail=f"Nao foi possivel carregar cookies no yt-dlp: {exc}") from exc
        errors.append(f"Erro ao inicializar yt-dlp: {exc}")
        return [], errors

    with ydl_ctx as ydl:
        for source in sources:
            try:
                ydl.download([source])
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{source}: {exc}")

    # Process and append logger messages to errors list
    for msg in logger.messages:
        if msg.startswith("ERROR: "):
            err_text = msg[7:].strip()
            if err_text.startswith("ERROR:"):
                err_text = err_text[6:].strip()
            if err_text and err_text not in errors:
                errors.append(err_text)
        elif msg.startswith("WARNING: "):
            warn_text = msg[9:].strip()
            if warn_text and warn_text not in errors:
                errors.append(warn_text)

    after = [path for path in target_dir.glob("**/*") if path.is_file() and path.resolve() not in before]
    videos = [
        {"path": str(path), "filename": path.name}
        for path in after
        if path.suffix.lower() in {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
    ]
    return videos, errors


def download_instagram_profiles_with_gallerydl(
    sources: list[str],
    limit: int,
    target_dir: Path,
    cookies_from_browser: str | None = None,
    cookies_file_path: str | None = None,
    offset: int = 0,
    on_file_done: Callable[[int], None] | None = None,
) -> tuple[list[dict[str, str]], list[str]]:
    """Baixa ate `limit` videos (Reels) de cada perfil do Instagram usando gallery-dl.

    O extractor de perfil do yt-dlp e instavel; o gallery-dl enumera perfis de forma
    confiavel. Cada perfil e resolvido para a aba de Reels (somente videos). O
    `--range` comeca em `offset + 1`, permitindo pular os videos mais recentes e
    baixar a partir de uma posicao arbitraria.
    """
    command = gallerydl_command()
    if command is None:
        raise HTTPException(
            status_code=501,
            detail=(
                "gallery-dl nao esta instalado. Rode o executor para reconstruir o ambiente "
                "ou instale backend/requirements.txt."
            ),
        )

    target_dir.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    before = {path.resolve() for path in target_dir.glob("**/*") if path.is_file()}

    video_filter = "extension in ('mp4', 'mov', 'm4v', 'webm', 'mkv')"
    base_args = [
        *command,
        "--no-colors",
        "--no-input",
        "--no-part",
        "--directory",
        str(target_dir),
        "--range",
        f"{offset + 1}-{offset + limit}",
        "--filter",
        video_filter,
    ]
    if cookies_file_path:
        base_args += ["--cookies", str(resolve_cookie_file(cookies_file_path))]
    elif cookies_from_browser:
        base_args += ["--cookies-from-browser", cookies_from_browser]

    for source in sources:
        username = instagram_profile_username(source)
        if not username:
            errors.append(f"{source}: URL de perfil do Instagram invalida para gallery-dl.")
            continue
        reels_url = f"https://www.instagram.com/{username}/reels/"
        try:
            result = subprocess.run(  # noqa: S603
                [*base_args, reels_url],
                capture_output=True,
                text=True,
                timeout=GALLERYDL_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            errors.append(f"{source}: gallery-dl excedeu o tempo limite ({GALLERYDL_TIMEOUT_SECONDS}s).")
            continue
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{source}: falha ao executar gallery-dl: {exc}")
            continue

        for line in (result.stderr or "").splitlines():
            cleaned = line.strip()
            if cleaned and cleaned not in errors:
                errors.append(cleaned)

        if on_file_done:
            current = sum(
                1
                for path in target_dir.glob("**/*")
                if path.is_file()
                and path.resolve() not in before
                and path.suffix.lower() in VIDEO_EXTENSIONS
            )
            on_file_done(current)

    after = [
        path
        for path in target_dir.glob("**/*")
        if path.is_file() and path.resolve() not in before
    ]
    videos = [
        {"path": str(path), "filename": path.name}
        for path in sorted(after, key=lambda item: item.name)
        if path.suffix.lower() in VIDEO_EXTENSIONS
    ]
    return videos, errors


DOWNLOAD_TERMINAL_STATUSES = {"completed", "completed_with_errors", "failed", "canceled"}


def serialize_download_job(job: DownloadJob) -> dict[str, Any]:
    cookies_mode = "file" if job.cookies_file_path else "browser" if job.cookies_browser else "none"
    return {
        "id": job.id,
        "status": job.status,
        "progress": job.progress,
        "current_step": job.current_step,
        "sources": json.loads(job.sources_json or "[]"),
        "limit": job.limit,
        "offset": job.offset,
        "import_to_library": bool(job.import_to_library),
        "cookies_mode": cookies_mode,
        "cookies_browser": job.cookies_browser,
        "downloaded_count": job.downloaded_count,
        "target_dir": job.target_dir,
        "downloaded": json.loads(job.downloaded_json or "[]"),
        "imported": json.loads(job.imported_json or "[]"),
        "errors": json.loads(job.errors_json or "[]"),
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }


def enqueue_download_job(
    db: Session,
    *,
    source: str,
    limit: int,
    rights_confirmed: bool,
    import_to_library: bool,
    offset: int = 0,
    cookies_from_browser: str | None = None,
    cookies_file_path: str | None = None,
    destination: str | None = None,
) -> DownloadJob:
    """Valida a requisicao de download de forma sincrona (erros retornam na hora) e
    enfileira um job. O download em si roda em background (worker/BackgroundTask)."""
    if not rights_confirmed:
        raise HTTPException(status_code=422, detail="Confirme que voce tem direito de baixar e reutilizar estes videos.")
    target_dir = resolve_download_target_dir(destination)
    browser = resolve_cookie_browser(cookies_from_browser)
    if browser and cookies_file_path:
        raise HTTPException(status_code=422, detail="Escolha apenas uma fonte de cookies: navegador ou arquivo cookies.txt.")
    if browser and not browser_cookie_import_supported():
        raise HTTPException(status_code=422, detail=COOKIE_FILE_HELP)
    sources = parse_sources(source)

    profile_sources = [item for item in sources if is_instagram_profile_url(item)]
    has_cookies = bool(browser or cookies_file_path)
    if profile_sources and not has_cookies:
        raise HTTPException(status_code=422, detail=INSTAGRAM_PROFILE_COOKIES_REQUIRED)
    if cookies_file_path:
        # Valida o arquivo de cookies antes de enfileirar.
        resolve_cookie_file(cookies_file_path)

    job = DownloadJob(
        sources_json=json.dumps(sources, ensure_ascii=False),
        limit=limit,
        offset=offset,
        import_to_library=1 if import_to_library else 0,
        cookies_browser=browser,
        cookies_file_path=cookies_file_path,
        target_dir=str(target_dir) if target_dir else None,
        status="queued",
        progress=0,
        current_step="Na fila",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    record_event(
        db,
        event_type="download_enqueued",
        entity_type="download_job",
        entity_id=job.id,
        message=f"Download enfileirado com {len(sources)} origem(ns), limite {limit}.",
        payload={"sources": sources, "limit": limit, "offset": offset},
    )
    return job


def next_queued_download_job(db: Session) -> DownloadJob | None:
    return (
        db.query(DownloadJob)
        .filter(DownloadJob.status == "queued")
        .order_by(DownloadJob.created_at.asc())
        .first()
    )


def claim_download_job(db: Session, job_id: str) -> DownloadJob | None:
    """Reserva atomicamente um job especifico (queued -> processing). Retorna None se
    outro processo/thread ja o reservou."""
    claimed = db.execute(
        update(DownloadJob)
        .where(DownloadJob.id == job_id, DownloadJob.status == "queued")
        .values(
            status="processing",
            progress=5,
            current_step="Reservado para download",
            attempts=DownloadJob.attempts + 1,
            started_at=now_utc(),
            error_message=None,
        )
    )
    db.commit()
    if claimed.rowcount != 1:
        return None
    return db.get(DownloadJob, job_id)


def claim_next_download_job(db: Session) -> DownloadJob | None:
    candidate = next_queued_download_job(db)
    if not candidate:
        return None
    return claim_download_job(db, candidate.id)


def recover_interrupted_download_jobs(db: Session) -> int:
    jobs = db.query(DownloadJob).filter(DownloadJob.status == "processing").all()
    if not jobs:
        return 0
    for job in jobs:
        job.status = "queued"
        job.progress = 0
        job.current_step = "Recuperado apos reinicio"
        job.error_message = "Download voltou para a fila porque o processo reiniciou."
        job.started_at = None
    db.commit()
    return len(jobs)


def process_download_job(db: Session, job: DownloadJob) -> DownloadJob:
    job.status = "processing"
    job.progress = 10
    job.current_step = "Preparando download"
    if job.attempts == 0:
        job.attempts = 1
    if job.started_at is None:
        job.started_at = now_utc()
    job.error_message = None
    db.commit()

    sources = json.loads(job.sources_json or "[]")
    profile_sources = [item for item in sources if is_instagram_profile_url(item)]
    direct_sources = [item for item in sources if not is_instagram_profile_url(item)]
    expected = max(1, job.limit * max(1, len(sources)))

    def report(done: int, step: str) -> None:
        job.downloaded_count = done
        job.progress = min(95, 10 + int(done / expected * 85))
        job.current_step = step
        db.commit()

    try:
        if job.target_dir:
            # Destino escolhido pelo usuario (definido no enqueue).
            target_dir = Path(job.target_dir)
        else:
            stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
            target_dir = INCOMING_DIR / "massloader" / f"{stamp}-{job.id[:8]}"
            job.target_dir = str(target_dir)
        db.commit()

        downloaded: list[dict[str, str]] = []
        errors: list[str] = []

        if direct_sources:
            job.current_step = "Baixando URLs diretas (yt-dlp)"
            db.commit()
            direct_downloaded, direct_errors = download_with_ytdlp(
                direct_sources,
                job.limit,
                target_dir,
                job.cookies_browser,
                job.cookies_file_path,
                job.offset,
                on_file_done=lambda done: report(done, "Baixando URLs diretas (yt-dlp)"),
            )
            downloaded += direct_downloaded
            errors += direct_errors

        if profile_sources:
            base_done = len(downloaded)
            job.current_step = "Baixando perfis do Instagram (gallery-dl)"
            db.commit()
            profile_downloaded, profile_errors = download_instagram_profiles_with_gallerydl(
                profile_sources,
                job.limit,
                target_dir,
                job.cookies_browser,
                job.cookies_file_path,
                job.offset,
                on_file_done=lambda done: report(base_done + done, "Baixando perfis do Instagram (gallery-dl)"),
            )
            downloaded += profile_downloaded
            errors += profile_errors

        imported: list[dict[str, str]] = []
        if job.import_to_library and downloaded:
            job.current_step = "Importando para a biblioteca"
            job.progress = 96
            db.commit()
            imported_assets = import_paths(db, [item["path"] for item in downloaded], copy_to_library=True)
            imported = [{"id": asset.id, "filename": asset.filename} for asset in imported_assets]

        errors = normalize_downloader_messages(errors, sources=sources, downloaded_count=len(downloaded))
        cookies_mode = "file" if job.cookies_file_path else "browser" if job.cookies_browser else "none"
        manifest = {
            "created_at": datetime.now(UTC).isoformat(),
            "sources": sources,
            "limit": job.limit,
            "offset": job.offset,
            "target_dir": str(target_dir),
            "cookies_mode": cookies_mode,
            "cookies_browser": job.cookies_browser,
            "downloaded": downloaded,
            "imported": imported,
            "errors": errors,
        }
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "massloader-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        job.downloaded_json = json.dumps(downloaded, ensure_ascii=False)
        job.imported_json = json.dumps(imported, ensure_ascii=False)
        job.errors_json = json.dumps(errors, ensure_ascii=False)
        job.downloaded_count = len(downloaded)
        job.progress = 100
        job.finished_at = now_utc()
        if not downloaded:
            job.status = "failed"
            job.current_step = "Nenhum video baixado"
            job.error_message = errors[0] if errors else "Nenhum video foi baixado."
        elif errors:
            job.status = "completed_with_errors"
            job.current_step = f"Concluido com avisos ({len(downloaded)} video(s))"
        else:
            job.status = "completed"
            job.current_step = f"Concluido ({len(downloaded)} video(s))"
        db.commit()
        record_event(
            db,
            event_type="download_completed" if downloaded else "download_failed",
            entity_type="download_job",
            entity_id=job.id,
            message=job.current_step,
            payload={"downloaded": len(downloaded), "imported": len(imported)},
        )
    except Exception as exc:  # noqa: BLE001
        job.status = "failed"
        job.progress = 100
        job.current_step = "Falhou"
        job.error_message = str(exc)
        job.finished_at = now_utc()
        db.commit()
        record_event(
            db,
            event_type="download_failed",
            entity_type="download_job",
            entity_id=job.id,
            message=str(exc),
            payload={"attempts": job.attempts},
        )
    db.refresh(job)
    return job


def run_download_job_in_background(job_id: str) -> None:
    """Executado via BackgroundTask do FastAPI: abre sua propria sessao, reserva o job
    e processa. Se o worker dedicado ja tiver reservado, apenas sai."""
    with SessionLocal() as db:
        job = claim_download_job(db, job_id)
        if job is None:
            return
        process_download_job(db, job)


instagram_status = massloader_status
