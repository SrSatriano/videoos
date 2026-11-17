from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ImportRequest(BaseModel):
    paths: list[str] = Field(min_length=1)
    copy_to_library: bool = True


class DeleteAssetsRequest(BaseModel):
    asset_ids: list[str] = Field(min_length=1, max_length=5000)


class TemplateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = ""
    recipe: dict[str, Any]


class TemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None
    recipe: dict[str, Any] | None = None


class TemplateDuplicateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)



class BatchCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    template_id: str
    asset_ids: list[str] = Field(min_length=1)
    variations: int = Field(default=1, ge=1, le=50)
    output_dir: str | None = Field(default=None, max_length=500)
    estimated_output_bytes: int | None = Field(default=None, ge=0)


class StorageCheckRequest(BaseModel):
    output_dir: str | None = Field(default=None, max_length=500)
    estimated_output_bytes: int = Field(ge=0)


class PublishPackageRequest(BaseModel):
    rendered_video_ids: list[str] = Field(min_length=1)
    platforms: list[Literal["instagram_reels", "tiktok", "youtube_shorts"]] = Field(
        default=["instagram_reels"]
    )
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    output_dir: str | None = None


class PublishTaskUpdate(BaseModel):
    status: Literal["ready", "posted", "failed", "archived"]


class RenderedVideoUpdate(BaseModel):
    status: Literal["pending_review", "approved", "rejected"]


class RetryRequest(BaseModel):
    reset_attempts: bool = False


class AgentRunRequest(BaseModel):
    agent_id: str
    brief: str = Field(min_length=3, max_length=4000)


class InstagramCaptureRequest(BaseModel):
    source: str = Field(min_length=5, max_length=4000)
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0, le=100000)
    rights_confirmed: bool = False
    import_to_library: bool = True
    cookies_from_browser: str | None = None
    cookies_file_path: str | None = None
    destination: str | None = Field(default=None, max_length=200)



class TranscriptionRequest(BaseModel):
    asset_id: str
    language: str = "pt"


class ManualTranscriptionRequest(BaseModel):
    asset_id: str
    text: str = Field(min_length=1, max_length=200000)
    language: str = "pt"


class TranscriptUpdateRequest(BaseModel):
    text: str | None = None
    segments: list[dict[str, Any]] | None = None
    words: list[dict[str, Any]] | None = None



class StructuredAgentRequest(BaseModel):
    agent_id: str
    role: str = "Assistente criativo local para videos curtos."
    brief: str = Field(min_length=3, max_length=4000)
    model: str | None = None


class ClipAnalyzeRequest(BaseModel):
    asset_id: str
    min_seconds: int = Field(default=12, ge=5, le=90)
    max_seconds: int = Field(default=45, ge=10, le=180)
    limit: int = Field(default=10, ge=1, le=50)


class ClipBatchRequest(BaseModel):
    template_id: str
    name: str = Field(default="", max_length=160)
    variations: int = Field(default=1, ge=1, le=50)


class CaptionExportRequest(BaseModel):
    segments: list[dict[str, Any]] = Field(default_factory=list)
    format: Literal["srt", "vtt"] = "srt"


class BrandKitCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    config: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False


class BrollSuggestRequest(BaseModel):
    segments: list[dict[str, Any]] = Field(default_factory=list)
    local_asset_keywords: list[str] = Field(default_factory=list)


class MusicBriefRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=1000)


class CalendarBuildRequest(BaseModel):
    start_at: datetime
    count: int = Field(default=7, ge=1, le=90)
    interval_minutes: int = Field(default=1440, ge=15, le=10080)
    platforms: list[str] = Field(default_factory=lambda: ["instagram_reels"])


class SceneDetectRequest(BaseModel):
    threshold: float = Field(default=0.35, ge=0.05, le=0.95)
    limit: int = Field(default=80, ge=1, le=300)


class MarkerCreateRequest(BaseModel):
    time_seconds: float = Field(ge=0)
    duration_seconds: float | None = Field(default=None, ge=0)
    label: str = Field(default="Marcador", min_length=1, max_length=160)
    color: str = Field(default="#51d88a", max_length=32)
    marker_type: Literal["note", "hook", "cut", "scene", "chapter"] = "note"
    notes: str = Field(default="", max_length=2000)


class QualityCheckRequest(BaseModel):
    platforms: list[Literal["instagram_reels", "tiktok", "youtube_shorts"]] = Field(
        default_factory=lambda: ["instagram_reels", "tiktok", "youtube_shorts"]
    )


class BatchQualityCheckRequest(BaseModel):
    platforms: list[Literal["instagram_reels", "tiktok", "youtube_shorts"]] = Field(
        default_factory=lambda: ["instagram_reels", "tiktok", "youtube_shorts"]
    )



class SettingsUpdateRequest(BaseModel):
    incoming_dir: str | None = None
    assets_dir: str | None = None
    renders_dir: str | None = None
    publish_packages_dir: str | None = None
    google_api_key: str | None = None
    gemini_model: str | None = None


class TestGoogleApiRequest(BaseModel):
    api_key: str | None = None
    model: str | None = None


class MineViralClipsRequest(BaseModel):
    min_seconds: int = Field(default=15, ge=5, le=120)
    max_seconds: int = Field(default=60, ge=10, le=300)
    target_count: int = Field(default=5, ge=1, le=20)


class CreateBatchFromClipsRequest(BaseModel):
    asset_id: str
    template_id: str
    clips: list[dict[str, Any]] = Field(min_length=1)
    batch_name: str = Field(default="", max_length=160)
    enable_captions: bool = Field(default=True)
    caption_style: str = Field(default="hormozi")
    enable_music: bool = Field(default=False)
    music_volume: float = Field(default=0.15, ge=0.01, le=1.0)
    enable_jumpcut: bool = Field(default=True)


class TtsSynthesizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    voice: str = Field(default="pt-BR-AntonioNeural")


class GenerateFacelessVideoRequest(BaseModel):
    topic: str | None = None
    script_text: str | None = None
    voice: str = Field(default="pt-BR-AntonioNeural")
    template_id: str | None = None
    enable_captions: bool = Field(default=True)
    caption_style: str = Field(default="hormozi")
    video_name: str | None = None
    scene_images: list[str] = Field(default_factory=list)



class GenerateSceneImageRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)
    aspect_ratio: str = Field(default="9:16")
    save_as_asset: bool = Field(default=True)
    provider: str = Field(default="auto")


class AutopilotPipelineRequest(BaseModel):
    asset_id: str | None = None
    source_url: str | None = None
    min_score: int = Field(default=70, ge=1, le=100)
    max_clips: int = Field(default=3, ge=1, le=20)
    enable_captions: bool = Field(default=True)
    caption_style: str = Field(default="hormozi")
    enable_music: bool = Field(default=False)
    music_volume: float = Field(default=0.15, ge=0.01, le=1.0)
    enable_jumpcut: bool = Field(default=True)
    batch_name: str | None = None

