from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def new_id() -> str:
    return uuid.uuid4().hex


def now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    original_path: Mapped[str] = mapped_column(Text, nullable=False)
    stored_path: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    orientation: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    thumbnail_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(default=now_utc)

    jobs: Mapped[list["RenderJob"]] = relationship(back_populates="asset")
    proxies: Mapped[list["AssetProxy"]] = relationship(back_populates="asset")
    markers: Mapped[list["SceneMarker"]] = relationship(back_populates="asset")


class AssetProxy(Base):
    __tablename__ = "asset_proxies"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), nullable=False, index=True)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(default=now_utc, onupdate=now_utc)

    asset: Mapped[Asset] = relationship(back_populates="proxies")


class SceneMarker(Base):
    __tablename__ = "scene_markers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), nullable=False, index=True)
    time_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    label: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    color: Mapped[str] = mapped_column(String(32), nullable=False, default="#51d88a")
    marker_type: Mapped[str] = mapped_column(String(40), nullable=False, default="note")
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="manual")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(default=now_utc)

    asset: Mapped[Asset] = relationship(back_populates="markers")


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    recipe_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(default=now_utc, onupdate=now_utc)

    jobs: Mapped[list["RenderJob"]] = relationship(back_populates="template")


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    template_id: Mapped[str] = mapped_column(ForeignKey("templates.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    total_jobs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_dir: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(default=now_utc)

    jobs: Mapped[list["RenderJob"]] = relationship(back_populates="batch")


class RenderJob(Base):
    __tablename__ = "render_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    batch_id: Mapped[str] = mapped_column(ForeignKey("batches.id"), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), nullable=False)
    template_id: Mapped[str] = mapped_column(ForeignKey("templates.id"), nullable=False)
    variation_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_step: Mapped[str] = mapped_column(String(120), nullable=False, default="Na fila")
    output_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(default=now_utc)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)

    batch: Mapped[Batch] = relationship(back_populates="jobs")
    asset: Mapped[Asset] = relationship(back_populates="jobs")
    template: Mapped[Template] = relationship(back_populates="jobs")
    rendered_video: Mapped["RenderedVideo | None"] = relationship(back_populates="job")


class RenderedVideo(Base):
    __tablename__ = "rendered_videos"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    job_id: Mapped[str] = mapped_column(ForeignKey("render_jobs.id"), unique=True, nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), nullable=False)
    template_id: Mapped[str] = mapped_column(ForeignKey("templates.id"), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    render_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    peak_rss_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quality_cache_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_review")
    created_at: Mapped[datetime] = mapped_column(default=now_utc)
    reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    job: Mapped[RenderJob] = relationship(back_populates="rendered_video")
    publish_tasks: Mapped[list["PublishTask"]] = relationship(back_populates="rendered_video")


class DownloadJob(Base):
    __tablename__ = "download_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    sources_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    limit: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    offset: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    import_to_library: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cookies_browser: Mapped[str | None] = mapped_column(String(40), nullable=True)
    cookies_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_step: Mapped[str] = mapped_column(String(160), nullable=False, default="Na fila")
    downloaded_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    target_dir: Mapped[str | None] = mapped_column(Text, nullable=True)
    downloaded_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    imported_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    errors_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(default=now_utc)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)


class PlatformPreset(Base):
    __tablename__ = "platform_presets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    platform: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False, default=1080)
    height: Mapped[int] = mapped_column(Integer, nullable=False, default=1920)
    codec: Mapped[str] = mapped_column(String(80), nullable=False, default="H.264/AAC")
    checklist_json: Mapped[str] = mapped_column(Text, nullable=False)
    rule_type: Mapped[str] = mapped_column(String(40), nullable=False, default="organic")
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_checked_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    max_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_file_size_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_bitrate_kbps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    safe_zone_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")


class PublishTask(Base):
    __tablename__ = "publish_tasks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    rendered_video_id: Mapped[str] = mapped_column(ForeignKey("rendered_videos.id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")
    package_dir: Mapped[str] = mapped_column(Text, nullable=False)
    caption: Mapped[str] = mapped_column(Text, nullable=False, default="")
    hashtags_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    checklist_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(default=now_utc, onupdate=now_utc)

    rendered_video: Mapped[RenderedVideo] = relationship(back_populates="publish_tasks")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(default=now_utc)


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
