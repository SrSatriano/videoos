from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .config import CORS_ALLOW_CREDENTIALS, CORS_ORIGINS, DATA_DIR, ensure_data_dirs

logger = logging.getLogger("videoos")

BLOCKED_MEDIA_SUBPATHS = ("/db", "massloader-cookies", "logs", "settings.json", ".env", ".git")
ALLOWED_MEDIA_EXTENSIONS = {
    ".mp4", ".mov", ".m4v", ".webm", ".mkv",
    ".jpg", ".jpeg", ".png", ".webp",
    ".wav", ".mp3", ".aac",
    ".srt", ".vtt", ".json", ".txt",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        return response


class SafeStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: dict) -> Response:
        normalized = "/" + path.lstrip("/").replace("\\", "/").lower()
        if any(blocked in normalized for blocked in BLOCKED_MEDIA_SUBPATHS):
            raise StarletteHTTPException(status_code=403, detail="Acesso proibido a este arquivo.")

        target_path = (Path(self.directory) / path.lstrip("/")).resolve()
        try:
            target_path.relative_to(Path(self.directory).resolve())
        except ValueError:
            raise StarletteHTTPException(status_code=403, detail="Acesso fora do diretorio permitido.")

        if target_path.is_file() and target_path.suffix.lower() not in ALLOWED_MEDIA_EXTENSIONS:
            raise StarletteHTTPException(status_code=403, detail="Tipo de arquivo nao permitido para visualizacao.")

        return await super().get_response(path, scope)


from .database import SessionLocal, init_db
from .routes import (
    agents,
    ai,
    assets,
    batches,
    brand_kits,
    broll,
    calendar,
    captions,
    clips,
    editor_tools,
    jobs,
    music,
    presets,
    publish,
    quality,
    social,
    system,
    templates,
    transcriptions,
)
from .services.render_metrics import backfill_render_metrics
from .services.seed import seed_defaults


def create_app() -> FastAPI:
    ensure_data_dirs()
    init_db()
    with SessionLocal() as db:
        seed_defaults(db)
        backfill_render_metrics(db)
        from .services.queue import recover_interrupted_jobs
        recover_interrupted_jobs(db)

    app = FastAPI(title="Sistema Pessoal de Edicao em Massa", version="0.1.0")
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "testserver", "host.docker.internal", "*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=CORS_ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def global_unhandled_exception_handler(request: Request, exc: Exception):
        if isinstance(exc, StarletteHTTPException):
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)
        if isinstance(exc, RequestValidationError):
            return JSONResponse(status_code=422, content={"detail": exc.errors()})
        logger.exception("Erro interno nao tratado na rota %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno no servidor ao processar requisicao."},
        )

    app.mount("/media", SafeStaticFiles(directory=DATA_DIR), name="media")
    app.include_router(system.router)
    app.include_router(ai.router)
    app.include_router(agents.router)
    app.include_router(assets.router)
    app.include_router(brand_kits.router)
    app.include_router(captions.router)
    app.include_router(clips.router)
    app.include_router(editor_tools.router)
    app.include_router(broll.router)
    app.include_router(music.router)
    app.include_router(calendar.router)
    app.include_router(presets.router)
    app.include_router(templates.router)
    app.include_router(batches.router)
    app.include_router(jobs.router)
    app.include_router(jobs.renders_router)
    app.include_router(publish.router)
    app.include_router(quality.router)
    app.include_router(social.router)
    app.include_router(transcriptions.router)
    return app


app = create_app()
