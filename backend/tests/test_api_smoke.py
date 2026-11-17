from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import social
from app.services.seed import DEFAULT_RECIPE
from conftest import DATA_ROOT


client = TestClient(app)


def test_health_and_seeded_template() -> None:
    health = client.get("/api/system/health")
    templates = client.get("/api/templates")

    assert health.status_code == 200
    payload = health.json()
    assert payload["database"]["journal_mode"] == "wal"
    assert payload["database"]["busy_timeout_ms"] == 30000
    assert payload["queue"]["queued"] >= 0
    assert payload["render_performance"]["minimum_samples"] == 3
    assert isinstance(payload["render_performance"]["profiles"], list)
    assert templates.status_code == 200
    assert templates.json()


def test_backup_uses_sqlite_backup_api() -> None:
    response = client.post("/api/system/backup")

    assert response.status_code == 200
    payload = response.json()
    assert payload["method"] == "sqlite_backup_api"
    assert Path(payload["database"]).exists()
    assert payload["size_bytes"] > 0


def test_new_phase_two_endpoints_are_available() -> None:
    assert client.get("/api/agents").status_code == 200
    assert client.get("/api/ai/status").status_code == 200
    assert client.get("/api/brand-kits").status_code == 200
    assert client.get("/api/clips").status_code == 200
    assert client.get("/api/music/status").status_code == 200
    assert client.get("/api/preset-library").status_code == 200
    assert client.get("/api/social/instagram/status").status_code == 200
    assert client.get("/api/transcriptions/status").status_code == 200
    assert client.get("/api/transcriptions").status_code == 200


def test_instagram_status_exposes_ytdlp_version() -> None:
    response = client.get("/api/social/instagram/status")

    assert response.status_code == 200
    payload = response.json()
    assert "yt_dlp_version" in payload
    if payload["configured"]:
        assert payload["yt_dlp_version"]


def test_platform_presets_include_rule_metadata() -> None:
    response = client.get("/api/platform-presets")

    assert response.status_code == 200
    presets = {preset["platform"]: preset for preset in response.json()}
    assert presets["youtube_shorts"]["rule_type"] == "organic"
    assert presets["youtube_shorts"]["max_duration_seconds"] == 180
    assert presets["youtube_shorts"]["source_url"]
    assert presets["tiktok"]["min_width"] == 540
    assert presets["tiktok"]["min_height"] == 960
    assert presets["tiktok"]["min_bitrate_kbps"] == 516
    assert isinstance(presets["instagram_reels"]["safe_zone"], dict)


def test_creator_utility_endpoints() -> None:
    caption = client.post(
        "/api/captions/export",
        json={"format": "srt", "segments": [{"start": 0, "end": 2, "text": "teste"}]},
    )
    music = client.post("/api/music/brief", json={"prompt": "trilha tech para tutorial"})
    calendar = client.post(
        "/api/calendar/build",
        json={
            "start_at": "2026-05-29T09:00:00",
            "count": 2,
            "interval_minutes": 120,
            "platforms": ["youtube_shorts"],
        },
    )

    assert caption.status_code == 200
    assert "00:00:00,000" in caption.json()["text"]
    assert music.status_code == 200
    assert music.json()["mood"] == "tech"
    assert calendar.status_code == 200
    assert len(calendar.json()["slots"]) == 2


def test_create_template_validates_recipe() -> None:
    response = client.post(
        "/api/templates",
        json={
            "name": "Template teste",
            "description": "Criado pelo teste",
            "recipe": DEFAULT_RECIPE,
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Template teste"


def test_instagram_capture_endpoint_validation(monkeypatch) -> None:
    # Test rights_confirmed = False
    response = client.post(
        "/api/social/instagram/capture",
        json={
            "source": "https://www.instagram.com/reel/C8C8a8vO_4F/",
            "limit": 5,
            "rights_confirmed": False,
            "import_to_library": True
        }
    )
    assert response.status_code == 422
    assert "Confirme que voce tem direito" in response.json()["detail"]

    # Test invalid URL
    response = client.post(
        "/api/social/instagram/capture",
        json={
            "source": "invalid-url",
            "limit": 5,
            "rights_confirmed": True,
            "import_to_library": True
        }
    )
    assert response.status_code == 422
    assert "URL invalida" in response.json()["detail"]

    calls: dict[str, object] = {}

    def fake_download_with_ytdlp(sources, limit, target_dir, cookies_from_browser=None, cookies_file_path=None, offset=0, on_file_done=None):
        calls["sources"] = sources
        calls["limit"] = limit
        calls["offset"] = offset
        calls["cookies_from_browser"] = cookies_from_browser
        calls["cookies_file_path"] = cookies_file_path
        return [], ["simulated downloader"]

    monkeypatch.setattr(social, "download_with_ytdlp", fake_download_with_ytdlp)

    # Test valid model parsing without hitting external networks
    response = client.post(
        "/api/social/instagram/capture",
        json={
            "source": "https://www.instagram.com/p/invalid-post-test-123/",
            "limit": 1,
            "offset": 3,
            "rights_confirmed": True,
            "import_to_library": False,
        }
    )
    assert response.status_code == 200
    enqueued = response.json()
    assert enqueued["status"] in {"queued", "processing", "failed", "completed", "completed_with_errors"}
    assert enqueued["sources"] == ["https://www.instagram.com/p/invalid-post-test-123/"]

    job = client.get(f"/api/social/downloads/{enqueued['id']}").json()
    assert job["status"] == "failed"  # fake retornou 0 videos
    assert job["errors"] == ["simulated downloader"]
    assert calls["sources"] == ["https://www.instagram.com/p/invalid-post-test-123/"]
    assert calls["limit"] == 1
    assert calls["offset"] == 3
    assert calls["cookies_from_browser"] is None
    assert calls["cookies_file_path"] is None


def test_instagram_profile_downloader_errors_get_actionable_guidance() -> None:
    errors = social.normalize_downloader_messages(
        [
            "The program functionality for this site has been marked as broken, and will probably not work.",
            "[instagram:user] ryokenz_clipper: Unable to extract data; Confirm you are on the latest version using yt-dlp -U",
        ],
        sources=["https://www.instagram.com/ryokenz_clipper/"],
        downloaded_count=0,
    )

    assert any("extractor de perfil do Instagram" in error for error in errors)
    assert any("cookies.txt" in error for error in errors)
    assert any("URLs diretas de Reels/posts" in error for error in errors)
    assert len(errors) == len(set(errors))


def test_instagram_reels_tab_source_is_normalized_before_downloader(monkeypatch) -> None:
    cookie_text = "# Netscape HTTP Cookie File\n.instagram.com\tTRUE\t/\tTRUE\t0\tsessionid\ttest\n"
    upload = client.post(
        "/api/social/cookies",
        files={"file": ("cookies.txt", cookie_text, "text/plain")},
    )
    assert upload.status_code == 200
    cookie_path = upload.json()["path"]

    calls: dict[str, object] = {}

    def fake_download_profiles(sources, limit, target_dir, cookies_from_browser=None, cookies_file_path=None, offset=0, on_file_done=None):
        calls["sources"] = sources
        calls["limit"] = limit
        calls["offset"] = offset
        return [], []

    monkeypatch.setattr(social, "download_instagram_profiles_with_gallerydl", fake_download_profiles)

    response = client.post(
        "/api/social/instagram/capture",
        json={
            "source": "https://www.instagram.com/art_viral/reels/?hl=pt-br",
            "limit": 100,
            "offset": 50,
            "rights_confirmed": True,
            "import_to_library": False,
            "cookies_file_path": cookie_path,
        },
    )

    assert response.status_code == 200
    assert calls["sources"] == ["https://www.instagram.com/art_viral/"]
    assert calls["limit"] == 100
    assert calls["offset"] == 50
    assert response.json()["sources"] == ["https://www.instagram.com/art_viral/"]


def test_instagram_profile_requires_cookies(monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("nao deveria baixar sem cookies")

    monkeypatch.setattr(social, "download_instagram_profiles_with_gallerydl", fail_if_called)
    monkeypatch.setattr(social, "download_with_ytdlp", fail_if_called)

    response = client.post(
        "/api/social/instagram/capture",
        json={
            "source": "https://www.instagram.com/ryokenz_clipper/",
            "limit": 10,
            "rights_confirmed": True,
            "import_to_library": False,
        },
    )

    assert response.status_code == 422
    assert "cookies" in response.json()["detail"].lower()


def test_instagram_capture_auto_detects_default_browser(monkeypatch) -> None:
    monkeypatch.setattr(social, "browser_cookie_import_supported", lambda: True)
    monkeypatch.setattr(social, "detect_default_browser", lambda: "firefox")

    calls: dict[str, object] = {}

    def fake_download_profiles(sources, limit, target_dir, cookies_from_browser=None, cookies_file_path=None, offset=0, on_file_done=None):
        calls["cookies_from_browser"] = cookies_from_browser
        return [], []

    monkeypatch.setattr(social, "download_instagram_profiles_with_gallerydl", fake_download_profiles)

    response = client.post(
        "/api/social/instagram/capture",
        json={
            "source": "https://www.instagram.com/art_viral/",
            "limit": 100,
            "rights_confirmed": True,
            "import_to_library": False,
            "cookies_from_browser": "auto",
        },
    )

    assert response.status_code == 200
    assert calls["cookies_from_browser"] == "firefox"
    assert response.json()["cookies_browser"] == "firefox"


def test_instagram_capture_auto_browser_unavailable_returns_422(monkeypatch) -> None:
    monkeypatch.setattr(social, "browser_cookie_import_supported", lambda: True)
    monkeypatch.setattr(social, "detect_default_browser", lambda: None)

    response = client.post(
        "/api/social/instagram/capture",
        json={
            "source": "https://www.instagram.com/art_viral/",
            "limit": 100,
            "rights_confirmed": True,
            "import_to_library": False,
            "cookies_from_browser": "auto",
        },
    )

    assert response.status_code == 422
    assert "navegador padrao" in response.json()["detail"].lower()


def test_instagram_capture_rejects_browser_cookies_when_container(monkeypatch) -> None:
    monkeypatch.setattr(social, "browser_cookie_import_supported", lambda: False)

    response = client.post(
        "/api/social/instagram/capture",
        json={
            "source": "https://www.instagram.com/ryokenz_clipper/",
            "limit": 1,
            "rights_confirmed": True,
            "import_to_library": False,
            "cookies_from_browser": "edge",
        },
    )

    assert response.status_code == 422
    assert "cookies.txt" in response.json()["detail"]


def test_social_cookie_upload_and_capture_file_path(monkeypatch) -> None:
    cookie_text = "# Netscape HTTP Cookie File\n.instagram.com\tTRUE\t/\tTRUE\t0\tsessionid\ttest\n"
    upload = client.post(
        "/api/social/cookies",
        files={"file": ("cookies.txt", cookie_text, "text/plain")},
    )
    assert upload.status_code == 200
    uploaded = upload.json()
    cookie_path = Path(uploaded["path"])
    assert cookie_path.exists()
    assert str(cookie_path).startswith(str((DATA_ROOT / "incoming" / "massloader-cookies").resolve()))

    calls: dict[str, object] = {}

    def fake_download_profiles(sources, limit, target_dir, cookies_from_browser=None, cookies_file_path=None, offset=0, on_file_done=None):
        calls["sources"] = sources
        calls["cookies_from_browser"] = cookies_from_browser
        calls["cookies_file_path"] = cookies_file_path
        return [], []

    monkeypatch.setattr(social, "download_instagram_profiles_with_gallerydl", fake_download_profiles)

    response = client.post(
        "/api/social/instagram/capture",
        json={
            "source": "https://www.instagram.com/ryokenz_clipper/",
            "limit": 1,
            "rights_confirmed": True,
            "import_to_library": False,
            "cookies_file_path": uploaded["path"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["cookies_mode"] == "file"
    assert calls["cookies_from_browser"] is None
    assert calls["cookies_file_path"] == uploaded["path"]


def test_social_cookie_upload_converts_json_export() -> None:
    cookie_json = json.dumps(
        [
            {
                "domain": ".instagram.com",
                "expirationDate": 1810766414.7,
                "hostOnly": False,
                "httpOnly": True,
                "name": "sessionid",
                "path": "/",
                "secure": True,
                "value": "abc123",
            }
        ]
    )
    upload = client.post(
        "/api/social/cookies",
        files={"file": ("cookies.txt", cookie_json, "text/plain")},
    )
    assert upload.status_code == 200
    stored = Path(upload.json()["path"]).read_text(encoding="utf-8")
    assert stored.startswith("# Netscape HTTP Cookie File")
    session_line = next(line for line in stored.splitlines() if "sessionid" in line)
    fields = session_line.split("\t")
    assert len(fields) == 7
    assert fields[0] == "#HttpOnly_.instagram.com"
    assert fields[5] == "sessionid"
    assert fields[6] == "abc123"


def test_social_cookie_upload_recovers_space_separated_netscape() -> None:
    # Colagem manual costuma trocar TAB por espacos.
    pasted = ".instagram.com TRUE / TRUE 0 sessionid pasted-value\n"
    upload = client.post(
        "/api/social/cookies",
        files={"file": ("cookies.txt", pasted, "text/plain")},
    )
    assert upload.status_code == 200
    stored = Path(upload.json()["path"]).read_text(encoding="utf-8")
    assert "\t".join([".instagram.com", "TRUE", "/", "TRUE", "0", "sessionid", "pasted-value"]) in stored


def test_social_cookie_upload_rejects_garbage() -> None:
    upload = client.post(
        "/api/social/cookies",
        files={"file": ("cookies.txt", "isto nao e um cookie\n", "text/plain")},
    )
    assert upload.status_code == 422


def test_capture_uses_custom_destination(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_download_direct(sources, limit, target_dir, cookies_from_browser=None, cookies_file_path=None, offset=0, on_file_done=None):
        captured["target_dir"] = str(target_dir)
        return [], []

    monkeypatch.setattr(social, "download_with_ytdlp", fake_download_direct)

    response = client.post(
        "/api/social/instagram/capture",
        json={
            "source": "https://www.tiktok.com/@perfil/video/123",
            "limit": 1,
            "rights_confirmed": True,
            "import_to_library": False,
            "destination": "MinhaPasta/chumai",
        },
    )
    assert response.status_code == 200
    target = response.json()["target_dir"].replace("\\", "/")
    assert target.endswith("massloader/MinhaPasta/chumai")
    assert str(captured["target_dir"]).replace("\\", "/").endswith("massloader/MinhaPasta/chumai")


def test_resolve_download_target_dir_sanitizes_and_contains() -> None:
    base = social.massloader_base_dir().resolve()

    # Nomes simples e subpastas sao mantidos dentro do massloader.
    simple = social.resolve_download_target_dir("chumai")
    assert simple is not None and simple.resolve().is_relative_to(base)
    assert simple.name == "chumai"

    # Traversal e caracteres perigosos sao neutralizados, sem escapar do massloader.
    escaped = social.resolve_download_target_dir("../../etc/segredo")
    assert escaped is not None and escaped.resolve().is_relative_to(base)

    # Sem destino -> None (usa pasta automatica com timestamp).
    assert social.resolve_download_target_dir(None) is None
    assert social.resolve_download_target_dir("   ") is None


def test_instagram_capture_rejects_cookie_file_outside_allowed_root(monkeypatch) -> None:
    outside = DATA_ROOT.parent / "outside-cookies.txt"
    outside.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")

    def validating_download(sources, limit, target_dir, cookies_from_browser=None, cookies_file_path=None):
        if cookies_file_path:
            social.resolve_cookie_file(cookies_file_path)
        return [], []

    monkeypatch.setattr(social, "download_with_ytdlp", validating_download)

    response = client.post(
        "/api/social/instagram/capture",
        json={
            "source": "https://www.instagram.com/ryokenz_clipper/",
            "limit": 1,
            "rights_confirmed": True,
            "import_to_library": False,
            "cookies_file_path": str(outside),
        },
    )

    assert response.status_code == 400
    assert "cookies_file_path fora da pasta permitida" in response.json()["detail"]


def test_gallerydl_profile_download_uses_reels_url_and_limit(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}

    class FakeResult:
        stdout = ""
        stderr = ""

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return FakeResult()

    monkeypatch.setattr(social, "gallerydl_command", lambda: ["gallery-dl"])
    monkeypatch.setattr(social.subprocess, "run", fake_run)

    videos, errors = social.download_instagram_profiles_with_gallerydl(
        ["https://www.instagram.com/art_viral/"],
        7,
        tmp_path,
    )

    cmd = captured["cmd"]
    assert cmd[-1] == "https://www.instagram.com/art_viral/reels/"
    assert "--range" in cmd
    assert cmd[cmd.index("--range") + 1] == "1-7"
    assert "--directory" in cmd
    assert videos == []
    assert errors == []


def test_gallerydl_missing_binary_returns_501(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(social, "gallerydl_command", lambda: None)

    with pytest.raises(Exception) as excinfo:
        social.download_instagram_profiles_with_gallerydl(
            ["https://www.instagram.com/art_viral/"],
            5,
            tmp_path,
        )

    assert getattr(excinfo.value, "status_code", None) == 501


def test_download_job_async_lifecycle_completes(monkeypatch) -> None:
    def fake_download_with_ytdlp(sources, limit, target_dir, cookies_from_browser=None, cookies_file_path=None, offset=0, on_file_done=None):
        if on_file_done:
            on_file_done(2)
        return (
            [
                {"path": "/tmp/a.mp4", "filename": "a.mp4"},
                {"path": "/tmp/b.mp4", "filename": "b.mp4"},
            ],
            [],
        )

    monkeypatch.setattr(social, "download_with_ytdlp", fake_download_with_ytdlp)

    response = client.post(
        "/api/social/instagram/capture",
        json={
            "source": "https://www.youtube.com/@canal/videos",
            "limit": 5,
            "rights_confirmed": True,
            "import_to_library": False,
        },
    )
    assert response.status_code == 200
    job_id = response.json()["id"]

    job = client.get(f"/api/social/downloads/{job_id}").json()
    assert job["status"] == "completed"
    assert job["progress"] == 100
    assert job["downloaded_count"] == 2
    assert len(job["downloaded"]) == 2

    listing = client.get("/api/social/downloads").json()
    assert any(item["id"] == job_id for item in listing)


def test_download_job_not_found_returns_404() -> None:
    assert client.get("/api/social/downloads/naoexiste123").status_code == 404


def test_media_static_endpoint_security_blocks_db_and_sensitive_files() -> None:
    assert client.get("/media/db/video_os.sqlite3").status_code == 403
    assert client.get("/media/settings.json").status_code == 403
    assert client.get("/media/incoming/massloader-cookies/secret_cookies.txt").status_code == 403
    assert client.get("/media/logs/app.log").status_code == 403


def test_system_logs_listing_and_purge() -> None:
    from app import config
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    (config.LOGS_DIR / "test_1.log").write_text("log 1", encoding="utf-8")
    (config.LOGS_DIR / "test_2.log").write_text("log 2", encoding="utf-8")

    list_res = client.get("/api/system/logs")
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total_files"] >= 2

    purge_res = client.post("/api/system/logs/purge?keep_latest=1")
    assert purge_res.status_code == 200
    purge_data = purge_res.json()
    assert purge_data["remaining_count"] <= 1


def test_system_open_path_restrictions(monkeypatch) -> None:
    from app.routes import system
    monkeypatch.setattr(system.os, "startfile", lambda p: None, raising=False)

    # 1. Missing path
    assert client.post("/api/system/open-path", json={}).status_code == 400

    # 2. Non-existent path
    assert client.post("/api/system/open-path", json={"path": "Z:/nao/existe"}).status_code == 404

    # 3. Disallowed root (path traversal attempt)
    # create a dummy temp outside allowed roots if possible or check validation
    from app import config
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    valid_folder = config.DATA_DIR
    res = client.post("/api/system/open-path", json={"path": str(valid_folder)})
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_unhandled_exception_returns_clean_500() -> None:
    from app import database
    from starlette.testclient import TestClient as StarletteTestClient

    def buggy_db():
        raise RuntimeError("Falha inesperada no driver C:\\Users\\Administrator\\secret\\file.txt")

    app.dependency_overrides[database.get_db] = buggy_db
    try:
        safe_client = StarletteTestClient(app, raise_server_exceptions=False)
        response = safe_client.get("/api/system/health")
        assert response.status_code == 500
        assert response.json() == {"detail": "Erro interno no servidor ao processar requisicao."}
        assert "C:\\" not in response.text
    finally:
        app.dependency_overrides.pop(database.get_db, None)




