# Video OS AI Studio Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Video OS into a local-first creator workstation with AI clipping, captions, brand templates, bulk publishing packages, music/stem tooling, and a cleaner professional interface.

**Architecture:** Keep the current Docker Compose + FastAPI + SQLite + worker + React stack. Add focused backend modules for transcripts, clip candidates, brand kits, b-roll, music assets, local LLM orchestration, and publication calendar. Keep social downloading and publishing semi-automatic, rights-confirmed, and without login bypass.

**Tech Stack:** FastAPI, SQLite WAL, SQLAlchemy, FFmpeg/FFprobe, yt-dlp for public/authorized downloads, optional faster-whisper for local transcription, optional PySceneDetect for scenes, optional Ollama for local LLM structured outputs, optional Demucs for audio stems, React + Vite + TypeScript + lucide-react.

---

## Research Summary

- Vizard focuses on long-video-to-short-video repurposing, auto clipping, dynamic captions, aspect ratio/crop/layout changes, transcription/translation, brand kit, and post scheduling. Source: https://vizard.ai/tools/ai-video-editor and https://docs.vizard.ai/docs/introduction
- OpusClip focuses on AI co-pilot prompts, local/URL uploads, trimming/extending, filler-word cleanup, B-roll, caption editing, layouts/reframing, brand templates, bulk download, XML export, and scheduling. Sources: https://help.opus.pro/docs/introduction, https://help.opus.pro/docs/article/layout-and-reframing, https://help.opus.pro/docs/article/ai-broll, https://help.opus.pro/docs/article/bulk-scheduler, https://help.opus.pro/docs/article/how-to-add-a-brand-template
- Suno Studio is a generative audio workstation concept: multitrack timeline, stem variations, BPM, volume/pitch controls, AI-assisted music generation, and exportable stems/MIDI. Suno also exposes stem extraction concepts and paid commercial-rights workflows. Sources: https://about.suno.com/blog/suno-studio, https://suno.com/l/vocal-isolator, https://suno.com/pricing
- Local implementation should use pragmatic local tools: faster-whisper for word timestamps/transcription, PySceneDetect for scenes, Ollama structured outputs for deterministic JSON agent responses, and Demucs optionally for stems. Sources: https://github.com/SYSTRAN/faster-whisper, https://www.scenedetect.com/docs/latest/, https://docs.ollama.com/capabilities/structured-outputs

## Product Shape

Video OS should become a desktop creator cockpit:

- **Home:** daily command center with cards for import, MassLoader, transcribe, find clips, render, review, publish.
- **Library:** media browser with filters, duplicates, source labels, transcript status, usage count.
- **AI Clips:** Vizard/Opus-style auto highlights with score, hook, reason, transcript snippet, and one-click batch render.
- **Caption Studio:** word-level captions, keyword highlight, emojis optional, filler removal, censor list, SRT/VTT export.
- **Brand Kit:** fonts, colors, logos, CTA overlays, intro/outro, caption styles, platform presets.
- **Templates:** visual recipes with layouts: fill, fit, split, screenshare, gameplay, CTA final, watermark, b-roll slots.
- **MassLoader:** queue for public/authorized downloads, manifests, retry, import-to-library.
- **Music Lab:** prompt-to-music-brief, local music library, stem extraction, vocal/instrumental preview, beat ducking.
- **Agents:** specialist agents for scripts, hooks, captions, SEO, thumbnails, b-roll, music, QA, calendar.
- **Calendar:** semi-automatic publishing plan with packages, captions, hashtags, checklist, and reminders.
- **System:** health, FFmpeg, Docker, queue, logs, backup, model availability.

## Safety And Scope

- Do not implement browser automation to bypass Instagram, TikTok, YouTube, login walls, private profiles, rate limits, or platform protections.
- MassLoader is for public or authorized content only, with a required rights checkbox and manifest audit.
- Do not auto-create or auto-operate social accounts. Store "profiles/brands/channels" locally as planning entities.
- Publishing remains semi-automatic in this plan: package generation, calendar, checklists, captions, hashtags, and user approval.
- Optional cloud APIs can be integrated later behind explicit API keys; the MVP path stays local-first.

## File Structure

### Backend

- Modify: `backend/app/models.py`
  - Add `BrandKit`, `Transcript`, `ClipCandidate`, `CaptionStyle`, `BrollCue`, `MusicTrack`, `MusicStem`, `CreatorProfile`, `ContentIdea`, `ScheduleSlot`.
- Modify: `backend/app/schemas.py`
  - Add request/response schemas for the new modules.
- Modify: `backend/app/main.py`
  - Register new routers.
- Modify: `backend/app/database.py`
  - Call schema upgrade helpers after `Base.metadata.create_all`.
- Create: `backend/app/services/migrations.py`
  - Idempotent SQLite column/table upgrade helpers.
- Create: `backend/app/services/llm.py`
  - Ollama status check and structured JSON prompt runner with deterministic fallback.
- Create: `backend/app/services/clip_analysis.py`
  - Transcript/scene-based candidate detection and scoring.
- Create: `backend/app/services/captions.py`
  - SRT/VTT generation, filler-word detection, word highlighting instructions.
- Create: `backend/app/services/brand_kit.py`
  - Brand kit defaults, validation, export/import.
- Create: `backend/app/services/broll.py`
  - B-roll cue generation and local asset matching.
- Create: `backend/app/services/audio_lab.py`
  - Audio extraction, music import, optional Demucs stem separation, loudness/ducking helpers.
- Create: `backend/app/services/calendar.py`
  - Local publishing plan generation.
- Create: `backend/app/routes/ai.py`
  - Local LLM status and agent runs.
- Create: `backend/app/routes/clips.py`
  - Auto-clipping APIs.
- Create: `backend/app/routes/brand_kits.py`
  - Brand kit CRUD/export/import.
- Create: `backend/app/routes/captions.py`
  - Caption generation/export.
- Create: `backend/app/routes/broll.py`
  - B-roll cue/list APIs.
- Create: `backend/app/routes/music.py`
  - Music Lab APIs.
- Create: `backend/app/routes/calendar.py`
  - Calendar APIs.
- Modify: `backend/app/services/render.py`
  - Support richer recipes: captions, layout modes, intro/outro, b-roll, music bed, ducking.
- Modify: `backend/app/services/seed.py`
  - Seed default brand kits, agents, caption styles, music moods, content pillars.
- Modify: `backend/requirements.txt`
  - Add optional but installable packages: `faster-whisper`, `scenedetect-headless`, `ollama`, and keep heavyweight audio separation disabled by default unless explicitly enabled.

### Frontend

- Modify: `frontend/src/types.ts`
  - Add types for all new entities.
- Modify: `frontend/src/api.ts`
  - Add API clients for new routers.
- Modify: `frontend/src/App.tsx`
  - Add new views and state refresh.
- Modify: `frontend/src/components/AppShell.tsx`
  - Add new navigation, command palette entry points, tooltips.
- Create: `frontend/src/components/HomeDesk.tsx`
  - Command center dashboard.
- Create: `frontend/src/components/AiClipsDesk.tsx`
  - Candidate list, scoring, transcript snippets, render buttons.
- Create: `frontend/src/components/BrandKitStudio.tsx`
  - Brand colors, fonts, logo, CTA, caption style editor.
- Create: `frontend/src/components/CaptionStudio.tsx`
  - Transcript/caption editor and export buttons.
- Create: `frontend/src/components/MusicLab.tsx`
  - Music library, stems, mood briefs, ducking settings.
- Create: `frontend/src/components/CalendarDesk.tsx`
  - Schedule cards, platform packages, status controls.
- Create: `frontend/src/components/CreatorProfiles.tsx`
  - Local brand/channel profiles and content pillars.
- Create: `frontend/src/components/ui/Button.tsx`
  - Icon-first button component with variants and tooltip support.
- Create: `frontend/src/components/ui/Card.tsx`
  - Flat compact cards with max 8px radius.
- Create: `frontend/src/components/ui/SegmentedControl.tsx`
  - Mode selector for layouts, platforms, statuses.
- Create: `frontend/src/components/ui/Tooltip.tsx`
  - Accessible hover/focus tooltip.
- Modify: `frontend/src/styles.css`
  - Replace the current one-note dark green/slate read with a balanced neutral cockpit palette, better density, refined cards, and responsive grids.

### Tests

- Create: `backend/tests/test_llm_structured.py`
- Create: `backend/tests/test_clip_analysis.py`
- Create: `backend/tests/test_caption_exports.py`
- Create: `backend/tests/test_brand_kits.py`
- Create: `backend/tests/test_music_lab.py`
- Create: `backend/tests/test_calendar.py`
- Modify: `backend/tests/test_render_recipe.py`
- Create: `frontend/src/components/__tests__/ui.test.tsx` if a frontend test runner is added.
- Keep smoke validation: `python -m pytest`, `npm run build`, `docker compose config`, `docker compose run --rm --no-deps api python -m pytest`, `docker compose run --rm --no-deps web npm run build`.

---

## Task 1: Schema Upgrade Foundation

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/database.py`
- Create: `backend/app/services/migrations.py`
- Test: `backend/tests/test_schema_upgrades.py`

- [ ] **Step 1: Write the failing schema test**

```python
from sqlalchemy import inspect

from app.database import SessionLocal, engine, init_db


def test_new_creator_tables_exist():
    init_db()
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    assert "brand_kits" in table_names
    assert "transcripts" in table_names
    assert "clip_candidates" in table_names
    assert "caption_styles" in table_names
    assert "broll_cues" in table_names
    assert "music_tracks" in table_names
    assert "music_stems" in table_names
    assert "creator_profiles" in table_names
    assert "content_ideas" in table_names
    assert "schedule_slots" in table_names


def test_default_brand_kit_can_be_inserted():
    init_db()
    with SessionLocal() as db:
        assert db.execute("select count(*) from brand_kits").scalar_one() >= 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `..\.venv\Scripts\python.exe -m pytest tests/test_schema_upgrades.py -v` from `backend`.

Expected: fail because tables do not exist.

- [ ] **Step 3: Add SQLAlchemy models**

Add these model classes to `backend/app/models.py` after `AuditEvent`:

```python
class BrandKit(Base):
    __tablename__ = "brand_kits"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    is_default: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(default=now_utc, onupdate=now_utc)


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), nullable=False, index=True)
    engine: Mapped[str] = mapped_column(String(80), nullable=False, default="faster-whisper")
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="pt")
    text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    segments_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    words_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    created_at: Mapped[datetime] = mapped_column(default=now_utc)


class ClipCandidate(Base):
    __tablename__ = "clip_candidates"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), nullable=False, index=True)
    transcript_id: Mapped[str | None] = mapped_column(ForeignKey("transcripts.id"), nullable=True)
    start_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    end_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    hook: Mapped[str] = mapped_column(String(220), nullable=False, default="")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="suggested")
    created_at: Mapped[datetime] = mapped_column(default=now_utc)
```

Continue the model block with:

```python
class CaptionStyle(Base):
    __tablename__ = "caption_styles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    brand_kit_id: Mapped[str | None] = mapped_column(ForeignKey("brand_kits.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(default=now_utc, onupdate=now_utc)


class BrollCue(Base):
    __tablename__ = "broll_cues"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), nullable=False, index=True)
    clip_candidate_id: Mapped[str | None] = mapped_column(ForeignKey("clip_candidates.id"), nullable=True)
    start_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    end_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    keyword: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="local")
    selected_asset_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=now_utc)


class MusicTrack(Base):
    __tablename__ = "music_tracks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    mood: Mapped[str] = mapped_column(String(80), nullable=False, default="creator")
    bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rights_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(default=now_utc)


class MusicStem(Base):
    __tablename__ = "music_stems"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    music_track_id: Mapped[str] = mapped_column(ForeignKey("music_tracks.id"), nullable=False, index=True)
    stem_type: Mapped[str] = mapped_column(String(40), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=now_utc)


class CreatorProfile(Base):
    __tablename__ = "creator_profiles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    niche: Mapped[str] = mapped_column(String(120), nullable=False, default="dicas tech")
    voice_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    platforms_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(default=now_utc, onupdate=now_utc)


class ContentIdea(Base):
    __tablename__ = "content_ideas"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    creator_profile_id: Mapped[str | None] = mapped_column(ForeignKey("creator_profiles.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    script: Mapped[str] = mapped_column(Text, nullable=False, default="")
    angle: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="idea")
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(default=now_utc)


class ScheduleSlot(Base):
    __tablename__ = "schedule_slots"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    publish_task_id: Mapped[str | None] = mapped_column(ForeignKey("publish_tasks.id"), nullable=True)
    platform: Mapped[str] = mapped_column(String(80), nullable=False)
    publish_at: Mapped[datetime] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="planned")
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(default=now_utc, onupdate=now_utc)
```

- [ ] **Step 4: Add migration helper**

Create `backend/app/services/migrations.py`:

```python
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


def run_schema_upgrades(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("pragma journal_mode=wal"))
        connection.execute(text("pragma busy_timeout=30000"))
```

Modify `backend/app/database.py` so `init_db()` calls `run_schema_upgrades(engine)` after `Base.metadata.create_all(bind=engine)`.

- [ ] **Step 5: Run tests**

Run: `..\.venv\Scripts\python.exe -m pytest tests/test_schema_upgrades.py -v` from `backend`.

Expected: pass.

---

## Task 2: Local LLM And Agent Orchestrator

**Files:**
- Create: `backend/app/services/llm.py`
- Create: `backend/app/routes/ai.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/services/agents.py`
- Test: `backend/tests/test_llm_structured.py`

- [ ] **Step 1: Write failing tests**

```python
from app.services.llm import fallback_structured_response, schema_for_agent_run


def test_fallback_structured_response_matches_schema():
    schema = schema_for_agent_run()
    result = fallback_structured_response("roteirista", "crie 3 ideias de dicas tech", schema)
    assert result["agent"] == "roteirista"
    assert len(result["items"]) == 3
    assert all("title" in item for item in result["items"])
```

- [ ] **Step 2: Implement structured LLM helper**

Create `backend/app/services/llm.py`:

```python
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


OLLAMA_URL = "http://host.docker.internal:11434/api/chat"


def schema_for_agent_run() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "agent": {"type": "string"},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "score": {"type": "number"},
                    },
                    "required": ["title", "description", "score"],
                },
            },
        },
        "required": ["agent", "items"],
    }


def fallback_structured_response(agent: str, brief: str, schema: dict[str, Any]) -> dict[str, Any]:
    cleaned = " ".join(brief.split())[:120]
    return {
        "agent": agent,
        "items": [
            {"title": f"Ideia {index}", "description": f"{cleaned} - angulo {index}", "score": 0.7}
            for index in range(1, 4)
        ],
    }


def run_ollama_structured(model: str, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "model": model,
        "stream": False,
        "format": schema,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": {"temperature": 0.2},
    }
    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        data = json.loads(response.read().decode("utf-8"))
    return json.loads(data["message"]["content"])
```

- [ ] **Step 3: Add route and register it**

Create `backend/app/routes/ai.py` with `GET /api/ai/status` and `POST /api/ai/agents/run`. Register it in `backend/app/main.py` with `app.include_router(ai.router)`.

- [ ] **Step 4: Seed specialist agents**

Add these presets to `backend/app/services/agents.py`:

```python
AGENT_PRESETS = [
    {"id": "roteirista", "name": "Roteirista Tech", "role": "Cria roteiros curtos para dicas tech em portugues."},
    {"id": "clipper", "name": "Cacador de Cortes", "role": "Encontra momentos fortes e transforma em shorts."},
    {"id": "hook", "name": "Editor de Gancho", "role": "Melhora os 3 primeiros segundos do video."},
    {"id": "caption", "name": "Legenda Viral", "role": "Cria legendas, captions e keywords destacadas."},
    {"id": "seo", "name": "SEO Social", "role": "Gera titulos, hashtags e descricoes por plataforma."},
    {"id": "broll", "name": "Curador de B-roll", "role": "Sugere cenas de apoio e assets locais."},
    {"id": "music", "name": "Diretor Musical", "role": "Cria briefs de trilha e moods para videos curtos."},
    {"id": "qa", "name": "Revisor Final", "role": "Checa legibilidade, audio, CTA e pacote final."},
]
```

- [ ] **Step 5: Run tests**

Run: `..\.venv\Scripts\python.exe -m pytest tests/test_llm_structured.py -v` from `backend`.

Expected: pass without Ollama installed because fallback is deterministic.

---

## Task 3: AI Clip Finder

**Files:**
- Create: `backend/app/services/clip_analysis.py`
- Create: `backend/app/routes/clips.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/schemas.py`
- Test: `backend/tests/test_clip_analysis.py`

- [ ] **Step 1: Write scoring tests**

```python
from app.services.clip_analysis import score_segment, split_transcript_into_candidates


def test_score_segment_rewards_hooks_and_cta():
    hot = score_segment("Voce esta perdendo dinheiro porque ainda faz isso manualmente")
    cold = score_segment("hoje eu acordei e abri o computador")
    assert hot > cold


def test_split_transcript_into_candidates_limits_duration():
    segments = [
        {"start": 0, "end": 8, "text": "primeiro ponto importante"},
        {"start": 8, "end": 20, "text": "segundo ponto com automacao"},
        {"start": 20, "end": 42, "text": "comenta eu quero para receber"},
    ]
    candidates = split_transcript_into_candidates(segments, min_seconds=10, max_seconds=35)
    assert candidates
    assert all(10 <= item["end_seconds"] - item["start_seconds"] <= 35 for item in candidates)
```

- [ ] **Step 2: Implement heuristics**

Create `backend/app/services/clip_analysis.py`:

```python
from __future__ import annotations

HOT_WORDS = ("perdendo", "segredo", "automatizar", "gratis", "erro", "dinheiro", "instagram", "comenta")


def score_segment(text: str) -> float:
    lowered = text.lower()
    score = 0.2
    score += min(0.4, len(text) / 400)
    score += sum(0.08 for word in HOT_WORDS if word in lowered)
    if "?" in text:
        score += 0.1
    if "comenta" in lowered or "eu quero" in lowered:
        score += 0.15
    return round(min(score, 1.0), 3)


def split_transcript_into_candidates(segments: list[dict], min_seconds: int, max_seconds: int) -> list[dict]:
    candidates: list[dict] = []
    for start_index, segment in enumerate(segments):
        text_parts = []
        start = float(segment["start"])
        end = float(segment["end"])
        for next_segment in segments[start_index:]:
            end = float(next_segment["end"])
            text_parts.append(str(next_segment["text"]))
            duration = end - start
            if duration >= min_seconds:
                text = " ".join(text_parts)
                candidates.append(
                    {
                        "start_seconds": start,
                        "end_seconds": min(end, start + max_seconds),
                        "score": score_segment(text),
                        "hook": text[:140],
                        "reason": "Corte sugerido por densidade de fala, palavras de impacto e CTA.",
                    }
                )
                break
            if duration > max_seconds:
                break
    return sorted(candidates, key=lambda item: item["score"], reverse=True)
```

- [ ] **Step 3: Add endpoints**

Create `backend/app/routes/clips.py`:

- `POST /api/clips/analyze` accepts `{ asset_id, min_seconds, max_seconds, limit }`.
- It loads the latest transcript for the asset.
- It calls `split_transcript_into_candidates`.
- It persists `ClipCandidate` rows.
- It returns candidates sorted by score.

- [ ] **Step 4: Register route and test**

Modify `backend/app/main.py` to include `clips.router`.

Run: `..\.venv\Scripts\python.exe -m pytest tests/test_clip_analysis.py -v` from `backend`.

Expected: pass.

---

## Task 4: Captions Studio

**Files:**
- Create: `backend/app/services/captions.py`
- Create: `backend/app/routes/captions.py`
- Modify: `backend/app/services/render.py`
- Modify: `backend/app/schemas.py`
- Create: `frontend/src/components/CaptionStudio.tsx`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/types.ts`
- Test: `backend/tests/test_caption_exports.py`

- [ ] **Step 1: Write caption export tests**

```python
from app.services.captions import build_srt, detect_filler_words


def test_build_srt_uses_timestamp_format():
    srt = build_srt([{"start": 1.2, "end": 3.4, "text": "fala importante"}])
    assert "00:00:01,200 --> 00:00:03,400" in srt
    assert "fala importante" in srt


def test_detect_filler_words_pt_br():
    result = detect_filler_words("tipo assim eu acho que voce sabe")
    assert "tipo" in result
    assert "assim" in result
```

- [ ] **Step 2: Implement caption service**

Create `backend/app/services/captions.py` with:

```python
FILLER_WORDS_PT = {"tipo", "assim", "ne", "cara", "entao", "basicamente"}


def format_srt_time(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, remainder = divmod(millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def build_srt(segments: list[dict]) -> str:
    blocks = []
    for index, segment in enumerate(segments, start=1):
        blocks.append(
            f"{index}\n{format_srt_time(float(segment['start']))} --> {format_srt_time(float(segment['end']))}\n{segment['text']}"
        )
    return "\n\n".join(blocks) + "\n"


def detect_filler_words(text: str) -> list[str]:
    words = [word.strip(".,!?;:").lower() for word in text.split()]
    return sorted({word for word in words if word in FILLER_WORDS_PT})
```

- [ ] **Step 3: Extend render recipe**

In `backend/app/services/render.py`, extend `build_video_filters` to accept `recipe["captions"]`:

```python
captions = recipe.get("captions", {})
if captions.get("enabled") and captions.get("burned_srt_path"):
    filters.append(f"subtitles='{escape_filter_path(captions['burned_srt_path'])}'")
```

- [ ] **Step 4: Add frontend view**

Create `frontend/src/components/CaptionStudio.tsx` with:

- asset selector
- transcript preview
- buttons: `Gerar SRT`, `Gerar VTT`, `Detectar vicios`, `Salvar estilo`
- segmented control: `Branco`, `Amarelo`, `Karaoke`, `Minimal`
- preview card showing 9:16 caption placement

- [ ] **Step 5: Run tests and build**

Run:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_caption_exports.py -v
cd ..\frontend
npm.cmd run build
```

Expected: tests pass and frontend builds.

---

## Task 5: Brand Kit And Template Studio V2

**Files:**
- Create: `backend/app/services/brand_kit.py`
- Create: `backend/app/routes/brand_kits.py`
- Modify: `backend/app/services/seed.py`
- Create: `frontend/src/components/BrandKitStudio.tsx`
- Create: `frontend/src/components/ui/Button.tsx`
- Create: `frontend/src/components/ui/Card.tsx`
- Create: `frontend/src/components/ui/SegmentedControl.tsx`
- Create: `frontend/src/components/ui/Tooltip.tsx`
- Modify: `frontend/src/components/TemplateStudio.tsx`
- Modify: `frontend/src/styles.css`
- Test: `backend/tests/test_brand_kits.py`

- [ ] **Step 1: Write validation tests**

```python
from app.services.brand_kit import normalize_brand_kit


def test_brand_kit_defaults_are_complete():
    kit = normalize_brand_kit({"name": "Dicas Tech"})
    assert kit["caption"]["font_size"] == 74
    assert kit["colors"]["primary"].startswith("#")
    assert kit["cta"]["text"]
```

- [ ] **Step 2: Implement defaults**

Create `backend/app/services/brand_kit.py`:

```python
DEFAULT_BRAND_KIT = {
    "colors": {"primary": "#63e28f", "accent": "#44a0ff", "text": "#ffffff", "outline": "#050607"},
    "caption": {"font_family": "Arial Bold", "font_size": 74, "position": "bottom", "keyword_color": "#ffd84d"},
    "cta": {"text": "Comenta 'eu quero' para receber", "position": "final"},
    "watermark": {"enabled": True, "text": "@seuperfil", "position": "bottom-right"},
    "layouts": ["fill", "fit", "screenshare"],
}


def normalize_brand_kit(payload: dict) -> dict:
    result = dict(DEFAULT_BRAND_KIT)
    for key, value in payload.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = {**result[key], **value}
        else:
            result[key] = value
    return result
```

- [ ] **Step 3: Build UI primitives**

Create reusable UI components with lucide icons, tooltip support, no nested cards, and border radius <= 8px.

- [ ] **Step 4: Upgrade Template Studio**

Add controls for:

- aspect ratio: 9:16, 1:1, 16:9 preview, but render MVP defaults to 9:16
- layout: fill, fit, split, screenshare, gameplay
- caption style: top/bottom, keyword color, outline, shadow
- intro/outro upload path
- CTA overlay text and timing
- logo/watermark
- safe-area grid preview

- [ ] **Step 5: Run tests/build**

Run `python -m pytest tests/test_brand_kits.py -v` and `npm.cmd run build`.

Expected: pass.

---

## Task 6: B-Roll Cue Engine

**Files:**
- Create: `backend/app/services/broll.py`
- Create: `backend/app/routes/broll.py`
- Modify: `backend/app/services/render.py`
- Create: `frontend/src/components/BrollDesk.tsx`
- Modify: `frontend/src/api.ts`
- Test: `backend/tests/test_broll.py`

- [ ] **Step 1: Write cue tests**

```python
from app.services.broll import suggest_broll_cues


def test_suggest_broll_cues_from_transcript():
    cues = suggest_broll_cues(
        [{"start": 0, "end": 5, "text": "abre o Instagram e automatiza as respostas"}],
        local_asset_keywords=["instagram", "automacao"],
    )
    assert cues[0]["keyword"] in {"instagram", "automacao"}
    assert cues[0]["start_seconds"] == 0
```

- [ ] **Step 2: Implement cue suggestions**

Create `backend/app/services/broll.py`:

```python
def suggest_broll_cues(segments: list[dict], local_asset_keywords: list[str]) -> list[dict]:
    cues = []
    for segment in segments:
        text = str(segment["text"]).lower()
        for keyword in local_asset_keywords:
            if keyword.lower() in text:
                cues.append(
                    {
                        "start_seconds": float(segment["start"]),
                        "end_seconds": float(segment["end"]),
                        "keyword": keyword,
                        "prompt": f"Mostrar apoio visual de {keyword}",
                        "source": "local",
                    }
                )
                break
    return cues
```

- [ ] **Step 3: Add UI**

Add a B-roll desk with:

- transcript sentence list
- suggested cues
- local asset picker
- buttons: `Aplicar`, `Regenerar sugestao`, `Remover`
- timeline rows with trim/extend controls

- [ ] **Step 4: Render integration**

Extend `RenderRecipe` to support:

```json
{
  "broll": [
    {"path": "data/assets/broll.mp4", "start": 3.0, "end": 7.0, "opacity": 1, "layout": "cover"}
  ]
}
```

Use FFmpeg `overlay` filters only after a backend test asserts the command includes the overlay input.

---

## Task 7: Music Lab And Suno-Style Audio Workflow

**Files:**
- Create: `backend/app/services/audio_lab.py`
- Create: `backend/app/routes/music.py`
- Modify: `backend/app/services/render.py`
- Create: `frontend/src/components/MusicLab.tsx`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api.ts`
- Test: `backend/tests/test_music_lab.py`

- [ ] **Step 1: Write audio tests**

```python
from app.services.audio_lab import build_music_duck_filter, music_brief_from_prompt


def test_music_brief_from_prompt():
    brief = music_brief_from_prompt("trilha tech futurista para tutorial rapido")
    assert brief["mood"] == "tech"
    assert "tutorial" in brief["description"]


def test_build_music_duck_filter():
    filter_value = build_music_duck_filter(video_has_voice=True)
    assert "sidechaincompress" in filter_value
```

- [ ] **Step 2: Implement Music Lab service**

Create `backend/app/services/audio_lab.py`:

```python
def music_brief_from_prompt(prompt: str) -> dict:
    lowered = prompt.lower()
    mood = "tech" if "tech" in lowered or "futur" in lowered else "creator"
    return {
        "mood": mood,
        "description": prompt.strip(),
        "bpm": 120 if mood == "tech" else 96,
        "usage": "background",
        "rights_note": "Use apenas trilhas proprias, licenciadas ou geradas com direito comercial.",
    }


def build_music_duck_filter(video_has_voice: bool) -> str:
    if video_has_voice:
        return "[1:a][0:a]sidechaincompress=threshold=0.08:ratio=8:attack=40:release=400[musicduck]"
    return "[1:a]volume=0.18[musicduck]"
```

- [ ] **Step 3: Add route**

Implement:

- `GET /api/music/tracks`
- `POST /api/music/import`
- `POST /api/music/brief`
- `POST /api/music/stems` returns unavailable unless Demucs is installed

- [ ] **Step 4: Add frontend**

Music Lab UI:

- prompt field: "Que vibe essa trilha deve ter?"
- buttons: `Gerar brief`, `Importar audio`, `Extrair stems`, `Aplicar ao render`
- stem cards: vocals, drums, bass, other, instrumental
- ducking slider 0-100
- licensing note always visible in compact text

- [ ] **Step 5: Optional Demucs install gate**

Keep Demucs disabled by default. Add system status:

```json
{"demucs_available": false, "reason": "Instale demucs no container para separar stems."}
```

Do not fail normal Video OS startup when Demucs is absent.

---

## Task 8: Publication Calendar And Bulk Packages

**Files:**
- Create: `backend/app/services/calendar.py`
- Create: `backend/app/routes/calendar.py`
- Modify: `backend/app/services/publisher.py`
- Create: `frontend/src/components/CalendarDesk.tsx`
- Modify: `frontend/src/components/PublishingDesk.tsx`
- Test: `backend/tests/test_calendar.py`

- [ ] **Step 1: Write calendar tests**

```python
from datetime import datetime

from app.services.calendar import build_schedule


def test_build_schedule_every_two_hours():
    slots = build_schedule(
        start_at=datetime(2026, 5, 29, 9, 0, 0),
        count=3,
        interval_minutes=120,
        platforms=["youtube_shorts"],
    )
    assert [slot["publish_at"].hour for slot in slots] == [9, 11, 13]
```

- [ ] **Step 2: Implement scheduler**

Create `backend/app/services/calendar.py`:

```python
from datetime import datetime, timedelta


def build_schedule(start_at: datetime, count: int, interval_minutes: int, platforms: list[str]) -> list[dict]:
    slots = []
    for index in range(count):
        for platform in platforms:
            slots.append(
                {
                    "publish_at": start_at + timedelta(minutes=interval_minutes * index),
                    "platform": platform,
                    "status": "planned",
                    "order_index": index + 1,
                }
            )
    return slots
```

- [ ] **Step 3: Enhance package files**

Modify publisher package output to include:

- `video.mp4`
- `thumbnail.jpg`
- `caption.txt`
- `hashtags.txt`
- `metadata.json`
- `checklist.md`
- `schedule.json`
- `quality-report.json`

- [ ] **Step 4: Calendar UI**

Add calendar page with:

- week grid
- platform filters
- drag/drop can wait; implement select + reschedule buttons first
- batch schedule button
- "Abrir pasta do pacote" link where supported

---

## Task 9: MassLoader V2

**Files:**
- Modify: `backend/app/services/social.py`
- Modify: `backend/app/routes/social.py`
- Modify: `frontend/src/components/CaptureDesk.tsx`
- Test: `backend/tests/test_massloader_queue.py`

- [ ] **Step 1: Write tests**

```python
from app.services.social import build_ytdlp_args


def test_ytdlp_args_include_limit_and_output_template():
    args = build_ytdlp_args("https://example.com/video", 5, "data/incoming/massloader")
    assert "--playlist-end" in args
    assert "5" in args
    assert "-o" in args
```

- [ ] **Step 2: Implement queue metadata**

Add MassLoader jobs with:

- source URL
- limit
- status
- downloaded count
- errors
- manifest path
- rights_confirmed
- created_at/finished_at

- [ ] **Step 3: UI buttons**

CaptureDesk should have:

- `Colar URL`
- `Baixar publicos/autorizados`
- `Parar fila`
- `Importar baixados`
- `Abrir pasta`
- per-item retry

Keep the rights checkbox required.

---

## Task 10: Visual System Upgrade

**Files:**
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/components/AppShell.tsx`
- Create: `frontend/src/components/HomeDesk.tsx`
- Create: `frontend/src/components/ui/Button.tsx`
- Create: `frontend/src/components/ui/Card.tsx`
- Create: `frontend/src/components/ui/Tooltip.tsx`

- [ ] **Step 1: Add neutral creator cockpit tokens**

In `styles.css`, add:

```css
:root {
  --bg: #0b0d10;
  --surface: #11151a;
  --surface-2: #171c22;
  --line: #27313a;
  --text: #f2f5f7;
  --muted: #9aa6b2;
  --green: #51d88a;
  --blue: #4da3ff;
  --yellow: #ffd166;
  --red: #ff7668;
}
```

- [ ] **Step 2: Replace hard-coded dominant colors gradually**

Replace repeated `#63e28f`, `#151a20`, `#202832`, `#8d98a8` with tokens. Keep the design dark, but add blue/yellow accents so it does not read as one-hue green.

- [ ] **Step 3: Add HomeDesk**

HomeDesk sections:

- "Fila de hoje"
- "Proximas acoes"
- "Clipes com maior score"
- "Pacotes prontos"
- "Saude do sistema"

Buttons:

- Importar
- MassLoader
- Transcrever
- Encontrar cortes
- Renderizar lote
- Revisar
- Gerar pacotes

- [ ] **Step 4: Responsive checks**

Run `npm.cmd run build`. Then open `http://127.0.0.1:5174` in the browser and verify:

- desktop 1440px: no text overlap
- tablet 1024px: nav collapses cleanly
- mobile 390px: cards stack, buttons fit, video cards keep 9:16

---

## Task 11: Render Engine V2

**Files:**
- Modify: `backend/app/services/render.py`
- Modify: `backend/app/schemas.py`
- Modify: `frontend/src/types.ts`
- Test: `backend/tests/test_render_recipe.py`

- [ ] **Step 1: Add tests for new recipe fields**

```python
from pathlib import Path

from app.services.render import build_ffmpeg_command


def test_render_recipe_supports_music_bed(sample_recipe):
    sample_recipe["music"] = {"enabled": True, "path": "data/assets/music.mp3", "volume": 0.18, "duck": True}
    command = build_ffmpeg_command(
        input_path=Path("input.mp4"),
        output_path=Path("out.mp4"),
        recipe=sample_recipe,
        variation_index=1,
    )
    assert "-filter_complex" in command or "-af" in command
```

- [ ] **Step 2: Extend recipe schema**

Add optional keys:

```json
{
  "layout": {"mode": "fill", "safe_area": true},
  "captions": {"enabled": true, "style_id": "", "burned_srt_path": ""},
  "broll": [],
  "music": {"enabled": false, "path": "", "volume": 0.18, "duck": true},
  "intro": {"enabled": false, "path": ""},
  "outro": {"enabled": false, "path": ""}
}
```

- [ ] **Step 3: Keep backward compatibility**

Existing recipes without these keys must still pass `validate_recipe`.

---

## Task 12: End-To-End Acceptance

**Files:**
- Modify: `README.md`
- Modify: `VideoOS.ps1` only if startup checks need new optional service statuses
- Test: existing backend/frontend/Docker checks

- [ ] **Step 1: Backend tests**

Run:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest
```

Expected: all tests pass.

- [ ] **Step 2: Frontend build**

Run:

```powershell
cd frontend
npm.cmd run build
```

Expected: Vite build completes.

- [ ] **Step 3: Docker verification**

Run:

```powershell
docker compose config
docker compose run --rm --no-deps api python -m pytest
docker compose run --rm --no-deps web npm run build
docker compose up -d --force-recreate --remove-orphans
```

Expected: API healthy on `http://127.0.0.1:8010`, frontend healthy on `http://127.0.0.1:5174`, FFmpeg available.

- [ ] **Step 4: Real workflow**

Use the two videos in `Planejamento`:

1. Import both videos.
2. Transcribe both videos.
3. Generate at least 10 clip candidates.
4. Create one brand kit.
5. Render 10 vertical variations.
6. Approve 3 renders.
7. Generate publishing packages for Instagram Reels, TikTok, and YouTube Shorts.
8. Create a 7-day calendar with at least 9 planned posts.

Expected: every package has `video.mp4`, `thumbnail.jpg`, `caption.txt`, `hashtags.txt`, `metadata.json`, `checklist.md`, `schedule.json`, and `quality-report.json`.

---

## Recommended Execution Order

1. Task 10: Visual System Upgrade
2. Task 1: Schema Upgrade Foundation
3. Task 2: Local LLM And Agent Orchestrator
4. Task 4: Captions Studio
5. Task 3: AI Clip Finder
6. Task 5: Brand Kit And Template Studio V2
7. Task 11: Render Engine V2
8. Task 8: Publication Calendar And Bulk Packages
9. Task 9: MassLoader V2
10. Task 6: B-Roll Cue Engine
11. Task 7: Music Lab And Suno-Style Audio Workflow
12. Task 12: End-To-End Acceptance

This order gives visible improvements early, then adds the AI-heavy workflow without breaking the current MVP.

## Definition Of Done

- The app looks like a polished local creator workstation, not a prototype dashboard.
- The main workflow is one-click understandable: import/download -> transcribe -> find clips -> apply brand kit -> render -> review -> package -> calendar.
- AI features degrade gracefully when Ollama/faster-whisper/Demucs are unavailable.
- All current MVP features continue to work.
- No cloud dependency is required for the core workflow.
- Downloading and publishing remain rights-aware and semi-automatic.
- Backend tests, frontend build, and Docker checks pass.

## Execution Options

1. **Subagent-Driven (recommended):** implement one task per fresh worker, review after each task, faster iteration with less context drift.
2. **Inline Execution:** implement in this thread in batches with checkpoints after visual, AI, render, and publishing modules.
