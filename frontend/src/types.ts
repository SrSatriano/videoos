export type Status = "queued" | "processing" | "completed" | "failed" | "canceled";

export interface Asset {
  id: string;
  filename: string;
  original_path: string;
  stored_path: string;
  sha256: string;
  size_bytes: number;
  duration_seconds: number | null;
  width: number | null;
  height: number | null;
  fps: number | null;
  orientation: string;
  metadata_status: string;
  thumbnail_url: string | null;
  media_url: string | null;
  created_at: string;
}

export interface AssetSmartBin {
  id: string;
  label: string;
  description: string;
  count: number;
  asset_ids: string[];
}

export interface AssetReindexResult {
  checked: number;
  repaired: number;
  failed: number;
  skipped: number;
  results: Array<{ id: string; filename: string; status: string; repaired: boolean }>;
}

export interface RenderRecipe {
  format: { width: number; height: number; fit: "crop" | "contain"; fps?: number };
  trim: { start: number; end: number | null };
  text: {
    top: string;
    bottom: string;
    font_size: number;
    font_color: string;
    border_color: string;
    border_width: number;
  };
  captions?: {
    enabled: boolean;
    burned_srt_path?: string;
    style?: "hormozi" | "neon_cyan" | "minimal_white" | "bold_red" | string;
  };
  jump_cut?: {
    enabled: boolean;
    noise_db?: number;
    min_silence_duration?: number;
  };
  layout?: "single" | "split_vertical" | "pip";
  split?: {
    secondary_video_path?: string;
    secondary_volume?: number;
  };
  hooks?: Array<{
    title?: string;
    top_text?: string;
    hook_video_path?: string;
  }>;
  frame?: {
    enabled: boolean;
    background_color: string;
    header_background_color: string;
    divider_color: string;
    divider_height: number;
    header_height: number;
    video_margin: number;
    video_fit: "crop" | "contain" | "blur_pad";
    logo_path: string;
    logo_size: number;
    channel_name: string;
    channel_color: string;
    channel_font_size: number;
  };
  broll?: Array<{ path: string; start: number; end: number; opacity?: number; layout?: "cover" | "contain" }>;
  watermark: { enabled: boolean; text: string; position: string };
  audio: {
    preserve: boolean;
    normalize: boolean;
    music_path?: string;
    music_volume?: number;
    original_volume?: number;
    fade_in?: number;
    fade_out?: number;
  };
  export: { codec: string; crf: number; preset: string };
}

export interface Template {
  id: string;
  name: string;
  description: string;
  recipe: RenderRecipe;
  created_at: string;
  updated_at: string;
}

export interface Batch {
  id: string;
  name: string;
  template_id: string;
  status: string;
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  canceled_jobs: number;
  active_jobs: number;
  retryable_jobs: number;
  output_dir: string | null;
  is_paused: boolean;
  created_at: string;
}

export interface RenderJob {
  id: string;
  batch_id: string;
  asset_id: string;
  template_id: string;
  variation_index: number;
  status: Status;
  progress: number;
  current_step: string;
  output_url: string | null;
  error_message: string | null;
  attempts: number;
  cancel_requested: boolean;
  asset_filename: string | null;
  template_name: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface RenderedVideo {
  id: string;
  job_id: string;
  asset_id: string;
  template_id: string;
  path: string;
  media_url: string | null;
  thumbnail_url: string | null;
  duration_seconds: number | null;
  width: number | null;
  height: number | null;
  size_bytes: number | null;
  render_seconds: number | null;
  peak_rss_bytes: number | null;
  status: "pending_review" | "approved" | "rejected";
  created_at: string;
  reviewed_at: string | null;
}

export interface RenderPerformanceProfile {
  template_id: string;
  resolution: "1080p" | "2k" | "4k";
  sample_count: number;
  wall_seconds_per_output_second: number;
  bytes_per_output_second: number;
  memory_sample_count: number;
  peak_memory_bytes: number | null;
  last_completed_at: string | null;
}

export interface RenderPerformanceSnapshot {
  minimum_samples: number;
  max_samples_per_profile: number;
  profiles: RenderPerformanceProfile[];
}

export interface StorageCapacityCheck {
  path: string;
  total_bytes: number;
  free_bytes: number;
  reserve_bytes: number;
  safe_available_bytes: number;
  estimated_output_bytes: number;
  required_bytes: number;
  estimate_buffer_ratio: number;
  has_capacity: boolean;
}

export interface PlatformPreset {
  id: string;
  platform: "instagram_reels" | "tiktok" | "youtube_shorts";
  label: string;
  width: number;
  height: number;
  codec: string;
  checklist: string[];
  rule_type: string;
  source_url: string | null;
  source_checked_at: string | null;
  max_duration_seconds: number | null;
  max_file_size_mb: number | null;
  min_width: number | null;
  min_height: number | null;
  min_bitrate_kbps: number | null;
  safe_zone: SafeZoneGuide;
  notes: string;
}

export interface PublishTask {
  id: string;
  rendered_video_id: string;
  platform: string;
  status: "ready" | "posted" | "failed" | "archived";
  package_dir: string;
  caption: string;
  hashtags: string[];
  checklist: string[];
  created_at: string;
}

export interface SystemHealth {
  status: string;
  ffmpeg: { available: boolean; ffmpeg: string | null; ffprobe: string | null };
  import_roots: string[];
  allowed_output_roots?: string[];
  database: {
    path: string;
    journal_mode: string;
    synchronous: number;
    busy_timeout_ms: number;
    wal_autocheckpoint: number;
  };
  storage?: {
    data_dir: string;
    assets_bytes: number;
    renders_bytes: number;
    proxies_bytes: number;
    thumbnails_bytes: number;
    publish_packages_bytes: number;
    db_bytes: number;
    logs_bytes: number;
    total_bytes: number;
  };
  counts: Record<string, number>;
  queue: Record<Status, number>;
  render_performance: RenderPerformanceSnapshot;
}

export interface AgentPreset {
  id: string;
  name: string;
  role: string;
}

export interface AgentRun {
  agent: AgentPreset;
  provider: string;
  model: string | null;
  output: string;
}

export interface InstagramStatus {
  configured: boolean;
  mode: string;
  yt_dlp_version?: string | null;
  gallery_dl_version?: string | null;
  gallery_dl_configured?: boolean;
  profile_downloads?: string;
  profile_requires_cookies?: boolean;
  default_browser?: string | null;
  target_dir?: string;
  cookies_dir?: string;
  cookie_file_upload?: boolean;
  cookie_file_extensions?: string[];
  browser_cookie_import_supported?: boolean;
  cookie_help?: string;
  requires_rights_confirmation: boolean;
}

export interface CookieUploadResult {
  path: string;
  filename: string;
  size_bytes: number;
}

export type DownloadJobStatus =
  | "queued"
  | "processing"
  | "completed"
  | "completed_with_errors"
  | "failed"
  | "canceled";

export interface DownloadJob {
  id: string;
  status: DownloadJobStatus;
  progress: number;
  current_step: string;
  sources: string[];
  limit: number;
  offset?: number;
  import_to_library?: boolean;
  cookies_mode?: "none" | "file" | "browser";
  cookies_browser?: string | null;
  downloaded_count: number;
  target_dir?: string | null;
  downloaded: Array<{ path: string; filename: string }>;
  imported: Array<{ id: string; filename: string }>;
  errors: string[];
  error_message?: string | null;
  created_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface DeleteAssetsResult {
  deleted: Array<{ id: string; filename: string }>;
  skipped: Array<{ id: string; filename: string; reason: string }>;
  missing: string[];
  deleted_count: number;
  skipped_count: number;
}

export interface TranscriptionStatus {
  available: boolean;
  engine: string;
  model: string;
}

export interface TranscriptionResult {
  asset_id: string;
  transcript_id?: string;
  path: string;
  text: string;
}

export interface Transcript {
  id: string;
  asset_id: string;
  engine: string;
  language: string;
  text: string;
  segments: Array<{ start: number; end: number; text: string }>;
  words: Array<Record<string, unknown>>;
  status: string;
  created_at: string;
}

export interface ClipCandidate {
  id: string;
  asset_id: string;
  transcript_id: string | null;
  start_seconds: number;
  end_seconds: number;
  score: number;
  hook: string;
  reason: string;
  status: "suggested" | "selected" | "rejected";
  created_at: string;
}

export interface BrandKitConfig {
  primary_color?: string;
  secondary_color?: string;
  accent_color?: string;
  background_color?: string;
  text_color?: string;
  font_family?: string;
  logo_url?: string;
  watermark_text?: string;
  divider_color?: string;
  karaoke_preset?: string;
  [key: string]: unknown;
}

export interface BrandKit {
  id: string;
  name: string;
  config: BrandKitConfig;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface AutopilotResult {
  status: string;
  batch_id: string;
  total_jobs: number;
  steps: string[];
}

export interface MusicStatus {
  demucs_available: boolean;
  message: string;
}

export interface MusicBrief {
  mood: string;
  description: string;
  bpm: number;
  usage: string;
  rights_note: string;
}

export interface CalendarSlot {
  id?: string;
  publish_at: string;
  platform: string;
  status: string;
  order_index: number;
  notes?: string;
  publish_task_id?: string | null;
  package_dir?: string | null;
  caption?: string | null;
}

export interface ViralHook {
  formula: string;
  formula_name: string;
  hook_text: string;
  target_seconds: number;
  retention_score: number;
  explanation: string;
}

export interface ScriptBlock {
  block: string;
  timing: string;
  goal: string;
  spoken_text: string;
  visual_cue: string;
  sfx_prompt?: string;
}

export interface BrollCue {
  start_seconds: number;
  end_seconds: number;
  keyword: string;
  prompt: string;
  source: string;
}

export interface PresetLibrary {
  counts: { templates: number; filters: number; masks: number; captions: number };
  templates: Array<{ id: string; name: string; description: string; recipe: RenderRecipe }>;
  filters: Array<{ id: string; name: string; category: string; ffmpeg: string }>;
  masks: Array<{ id: string; name: string; shape: string; opacity: number; feather: number }>;
  captions: Array<{
    id: string;
    name: string;
    mode: string;
    font_size: number;
    font_color: string;
    outline: string;
    box: boolean;
    keyword_color: string;
  }>;
}

export interface AssetProxy {
  id: string;
  asset_id: string;
  path: string;
  media_url: string | null;
  width: number | null;
  height: number | null;
  size_bytes: number;
  status: "ready" | "failed" | string;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface SceneMarker {
  id: string;
  asset_id: string;
  time_seconds: number;
  duration_seconds: number | null;
  label: string;
  color: string;
  marker_type: "note" | "hook" | "cut" | "scene" | "chapter" | string;
  source: string;
  notes: string;
  created_at: string;
}

export interface ExportPreset {
  id: string;
  name: string;
  category: string;
  description: string;
  width: number;
  height: number;
  codec: string;
  crf: number;
  preset: string;
  use_case: string;
}

export interface QualityIssue {
  severity: "error" | "warning" | "info";
  code?: string;
  message: string;
  fix: string;
}

export interface SafeZoneGuide {
  platform: PlatformPreset["platform"] | "universal";
  label: string;
  top_pct: number;
  right_pct: number;
  bottom_pct: number;
  left_pct: number;
  notes: string[];
}

export interface QualityReport {
  platform: PlatformPreset["platform"];
  label: string;
  passed: boolean;
  score: number;
  issues: QualityIssue[];
  safe_zone: SafeZoneGuide;
}

export interface QualityCheckResult {
  rendered_video_id: string;
  review_status: RenderedVideo["status"];
  package_ready: boolean;
  analysis_cache: {
    status: "hit" | "miss";
    schema_version: string;
    file_sha256: string;
    analyzed_at: string | null;
  };
  audio_issues: QualityIssue[];
  metadata: {
    width: number | null;
    height: number | null;
    duration_seconds: number | null;
    fps: number | null;
    size_bytes: number;
    aspect_ratio: number | null;
    orientation: string;
    bitrate_kbps: number | null;
    render_seconds: number | null;
    peak_rss_bytes: number | null;
    video_codec?: string | null;
    audio_codec?: string | null;
    audio_sample_rate_hz?: number | null;
    audio_channels?: number | null;
    has_audio?: boolean | null;
    container_format?: string | null;
    format_bit_rate_kbps?: number | null;
    loudness?: {
      status: "measured" | "silent" | "no_audio" | "unavailable";
      integrated_lufs?: number | null;
      true_peak_dbtp?: number | null;
      loudness_range_lu?: number | null;
      threshold_lufs?: number | null;
      target_integrated_lufs?: number;
      target_true_peak_dbtp?: number;
      target_lra_lu?: number;
    };
    path: string;
  };
  reports: QualityReport[];
  safe_zone_guide: SafeZoneGuide;
}

export interface BatchQualityItem {
  rendered_video_id: string;
  filename: string;
  status: RenderedVideo["status"];
  passed: boolean;
  score: number;
  audio_issues: QualityIssue[];
  reports: QualityReport[];
}

export interface BatchQualitySummary {
  batch_id: string;
  batch_name: string;
  total_renders: number;
  passed_count: number;
  error_count: number;
  warning_count: number;
  pass_rate: number;
  average_score: number;
  items: BatchQualityItem[];
}

export interface PackageQualityReport {
  schema_version: string;
  rendered_video_id: string;
  platform: string;
  platform_label: string;
  source: string;
  actual: {
    width?: number | null;
    height?: number | null;
    duration_seconds?: number | null;
    status?: string;
    file_size_bytes?: number | null;
    fps?: number | null;
    bitrate_kbps?: number | null;
    video_codec?: string | null;
    audio_codec?: string | null;
    loudness?: QualityCheckResult["metadata"]["loudness"];
  };
  checks: Array<{
    id: string;
    label: string;
    expected: unknown;
    actual: unknown;
    passed: boolean;
  }>;
  audio_issues?: QualityIssue[];
  passed: boolean;
  score: number;
}

export interface AuditEvent {
  id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  message: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface IntegrityCheckResult {
  valid: boolean;
  error_type: "file_missing" | "metadata_corrupt" | "no_video_stream" | "decode_failed" | "check_timeout_or_failed" | null;
  message: string;
  fix?: string;
  details?: {
    size_bytes: number;
    width: number | null;
    height: number | null;
    duration: number | null;
  };
}

export interface SystemSettings {
  incoming_dir: string;
  assets_dir: string;
  renders_dir: string;
  publish_packages_dir: string;
  allowed_output_roots?: string[];
  google_api_key_configured?: boolean;
  google_api_key_masked?: string;
  gemini_model?: string;
}

export interface SettingsUpdateRequest {
  incoming_dir?: string | null;
  assets_dir?: string | null;
  renders_dir?: string | null;
  publish_packages_dir?: string | null;
  google_api_key?: string | null;
  gemini_model?: string | null;
}

export interface AiProvidersStatus {
  google: {
    configured: boolean;
    model: string;
    masked_key: string;
  };
  ollama: {
    available: boolean;
    models: string[];
    url: string;
    tried_urls: string[];
  };
  tts: {
    available: boolean;
    engine: string;
    default_voice: string;
    voices_count: number;
  };
  whisper: {
    available: boolean;
    model: string;
  };
}

export interface TtsVoice {
  id: string;
  name: string;
  gender: string;
  lang: string;
}

export interface TtsSynthesizeResult {
  audio_path: string;
  audio_url?: string;
  srt_content?: string;
  srt_path?: string;
  voice: string;
  char_count: number;
}

export interface MinedClip {
  id?: string;
  start_seconds: number;
  end_seconds: number;
  duration: number;
  viral_score: number;
  hook: string;
  category: string;
  suggested_title: string;
  suggested_copy: string;
  suggested_hashtags: string[];
  reason: string;
  status?: string;
}

export interface MinedClipsResponse {
  asset_id: string;
  engine: string;
  count: number;
  clips: MinedClip[];
}

export interface GeneratedScriptBlock {
  block_name: string;
  timing: string;
  spoken_text: string;
  visual_direction: string;
  visual_prompt?: string;
  keyword?: string;
}

export interface GeneratedScriptResponse {
  title: string;
  target_duration: string;
  word_count: number;
  full_narration: string;
  blocks: GeneratedScriptBlock[];
  suggested_hashtags?: string[];
  suggested_audio_mood?: string;
}

export interface GenerateFacelessVideoPayload {
  topic?: string;
  script_text?: string;
  voice?: string;
  template_id?: string;
  enable_captions?: boolean;
  caption_style?: string;
  video_name?: string;
  scene_images?: string[];
}

export interface GenerateFacelessVideoResponse {
  status: string;
  batch_id: string;
  job_id: string;
  title: string;
  narration: string;
  tts: TtsSynthesizeResult;
  script?: GeneratedScriptResponse;
}

export interface GenerateSceneImagePayload {
  prompt: string;
  aspect_ratio?: string;
  save_as_asset?: boolean;
  provider?: string;
}

export interface GenerateSceneImageResponse {
  status: string;
  image_path: string;
  image_url: string;
  filename: string;
  prompt: string;
  provider: string;
  width: number;
  height: number;
  asset_id?: string;
}

export interface AutopilotPipelinePayload {
  asset_id?: string;
  source_url?: string;
  min_score?: number;
  max_clips?: number;
  enable_captions?: boolean;
  caption_style?: string;
  enable_music?: boolean;
  music_volume?: number;
  enable_jumpcut?: boolean;
  batch_name?: string;
}

export interface AutopilotPipelineResponse {
  status: string;
  batch_id: string;
  batch_name: string;
  asset: {
    id: string;
    filename: string;
    duration?: number;
  };
  total_jobs: number;
  clips_evaluated: number;
  clips_selected: number;
  clips: MinedClip[];
  conditional_editing: {
    captions: boolean;
    caption_style: string;
    music: boolean;
    music_volume: number;
    jumpcut: boolean;
  };
}

