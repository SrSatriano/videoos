import type {
  Asset,
  AgentPreset,
  AgentRun,
  Batch,
  BatchQualitySummary,
  BrandKit,
  BrollCue,
  CalendarSlot,
  ClipCandidate,
  CookieUploadResult,
  DeleteAssetsResult,
  DownloadJob,
  ExportPreset,
  InstagramStatus,
  MusicBrief,
  MusicStatus,
  PackageQualityReport,
  PlatformPreset,
  PresetLibrary,
  PublishTask,
  QualityCheckResult,
  RenderJob,
  RenderRecipe,
  RenderedVideo,
  AssetProxy,
  AssetSmartBin,
  AssetReindexResult,
  SceneMarker,
  SystemHealth,
  StorageCapacityCheck,
  Template,
  Transcript,
  TranscriptionResult,
  TranscriptionStatus,
  AuditEvent,
  IntegrityCheckResult,
  SystemSettings,
  SettingsUpdateRequest,
  AutopilotResult,
  ScriptBlock,
  ViralHook,
  AiProvidersStatus,
  TtsVoice,
  TtsSynthesizeResult,
  MinedClip,
  MinedClipsResponse,
  GeneratedScriptResponse,
  GenerateFacelessVideoPayload,
  GenerateFacelessVideoResponse,
  GenerateSceneImagePayload,
  GenerateSceneImageResponse,
  AutopilotPipelinePayload,
  AutopilotPipelineResponse
} from "./types";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const API_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS ?? 30000);

function createTimeoutSignal(customTimeoutMs?: number): { signal: AbortSignal; cleanup: () => void } {
  const timeoutMs = customTimeoutMs ?? API_TIMEOUT_MS;
  const timeoutFn = AbortSignal.timeout;
  if (typeof timeoutFn === "function") {
    return { signal: timeoutFn(timeoutMs), cleanup: () => undefined };
  }

  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  return { signal: controller.signal, cleanup: () => window.clearTimeout(timeoutId) };
}

function absoluteMediaUrl(path: string | null): string | null {
  if (!path) return null;
  if (path.startsWith("http")) return path;
  return `${API_BASE}${path}`;
}

async function request<T>(path: string, init?: RequestInit, customTimeoutMs?: number): Promise<T> {
  const timeout = createTimeoutSignal(customTimeoutMs);
  const isFormData = init?.body instanceof FormData;
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: isFormData ? init?.headers : { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      ...init,
      signal: timeout.signal
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail));
    }
    if (response.status === 204) {
      return {} as T;
    }
    const text = await response.text();
    return (text ? JSON.parse(text) : {}) as T;
  } catch (err) {
    if (err instanceof DOMException && ["AbortError", "TimeoutError"].includes(err.name)) {
      throw new Error("Tempo esgotado ao conectar com a API local.");
    }
    throw err;
  } finally {
    timeout.cleanup();
  }
}

function normalizeAsset(asset: Asset): Asset {
  return {
    ...asset,
    media_url: absoluteMediaUrl(asset.media_url),
    thumbnail_url: absoluteMediaUrl(asset.thumbnail_url)
  };
}

function normalizeRender(render: RenderedVideo): RenderedVideo {
  return {
    ...render,
    media_url: absoluteMediaUrl(render.media_url),
    thumbnail_url: absoluteMediaUrl(render.thumbnail_url)
  };
}

function normalizeProxy(proxy: AssetProxy): AssetProxy {
  return {
    ...proxy,
    media_url: absoluteMediaUrl(proxy.media_url)
  };
}

export const api = {
  health: () => request<SystemHealth>("/api/system/health", undefined, 5000),
  checkStorage: (payload: { output_dir?: string | null; estimated_output_bytes: number }) =>
    request<StorageCapacityCheck>("/api/system/storage-check", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  backup: () => request<{ database: string; created_at: string }>("/api/system/backup", { method: "POST" }),
  audit: () => request<AuditEvent[]>("/api/system/audit"),
  agents: () => request<AgentPreset[]>("/api/agents"),
  runAgent: (payload: { agent_id: string; brief: string }) =>
    request<AgentRun>("/api/agents/run", { method: "POST", body: JSON.stringify(payload) }),
  instagramStatus: () => request<InstagramStatus>("/api/social/instagram/status"),
  uploadInstagramCookies: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<CookieUploadResult>("/api/social/cookies", {
      method: "POST",
      body: formData
    });
  },
  captureInstagram: (payload: {
    source: string;
    limit: number;
    offset?: number;
    rights_confirmed: boolean;
    import_to_library: boolean;
    cookies_from_browser?: string | null;
    cookies_file_path?: string | null;
    destination?: string | null;
  }) =>
    request<DownloadJob>("/api/social/instagram/capture", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  getDownloadJob: (jobId: string) => request<DownloadJob>(`/api/social/downloads/${jobId}`),
  listDownloadJobs: () => request<DownloadJob[]>("/api/social/downloads"),

  transcriptionStatus: () => request<TranscriptionStatus>("/api/transcriptions/status"),
  transcriptions: (assetId?: string) => request<Transcript[]>(assetId ? `/api/transcriptions?asset_id=${assetId}` : "/api/transcriptions"),
  transcribeAsset: (payload: { asset_id: string; language: string }) =>
    request<TranscriptionResult>("/api/transcriptions", { method: "POST", body: JSON.stringify(payload) }),
  createManualTranscription: (payload: { asset_id: string; text: string; language: string }) =>
    request<Transcript>("/api/transcriptions/manual", { method: "POST", body: JSON.stringify(payload) }),
  updateTranscription: (id: string, payload: { text?: string; segments?: Array<Record<string, unknown>>; words?: Array<Record<string, unknown>> }) =>
    request<Transcript>(`/api/transcriptions/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  aiStatus: () => request<{ available: boolean; models: string[]; url: string }>("/api/ai/status"),
  runStructuredAgent: (payload: { agent_id: string; role: string; brief: string; model?: string | null }) =>
    request<{ agent: string; items: Array<{ title: string; description: string; score: number }> }>("/api/ai/agents/run", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  clips: () => request<ClipCandidate[]>("/api/clips"),
  analyzeClips: (payload: { asset_id: string; min_seconds: number; max_seconds: number; limit: number }) =>
    request<ClipCandidate[]>("/api/clips/analyze", { method: "POST", body: JSON.stringify(payload) }),
  createClipBatch: (clipId: string, payload: { template_id: string; name: string; variations: number }) =>
    request<{ clip: ClipCandidate; template: Template; batch: Batch }>(`/api/clips/${clipId}/create-batch`, {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  brandKits: () => request<BrandKit[]>("/api/brand-kits"),
  getBrandKit: (id: string) => request<BrandKit>(`/api/brand-kits/${id}`),
  createBrandKit: (payload: { name: string; config: Record<string, unknown>; is_default: boolean }) =>
    request<BrandKit>("/api/brand-kits", { method: "POST", body: JSON.stringify(payload) }),
  updateBrandKit: (id: string, payload: { name?: string; config?: Record<string, unknown>; is_default?: boolean }) =>
    request<BrandKit>(`/api/brand-kits/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteBrandKit: (id: string) =>
    request<{ ok: boolean }>(`/api/brand-kits/${id}`, { method: "DELETE" }),
  exportCaptions: (payload: { segments: Array<Record<string, unknown>>; format: "srt" | "vtt" }) =>
    request<{ format: string; text: string }>("/api/captions/export", { method: "POST", body: JSON.stringify(payload) }),
  captionFillers: (payload: { segments: Array<Record<string, unknown>> }) =>
    request<{ words: string[] }>("/api/captions/fillers", { method: "POST", body: JSON.stringify(payload) }),
  suggestBroll: (payload: { segments: Array<Record<string, unknown>>; local_asset_keywords: string[] }) =>
    request<{ cues: BrollCue[] }>("/api/broll/suggest", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  autoMatchBroll: (payload: { segments: Array<Record<string, unknown>>; available_brolls: Array<Record<string, unknown>>; max_overlays?: number }) =>
    request<{ overlays: Array<Record<string, unknown>>; count: number }>("/api/broll/auto-match", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  musicStatus: () => request<MusicStatus>("/api/music/status"),
  separateStems: (audioPath: string) =>
    request<{ status: string; engine: string; vocals_path?: string; instrumental_path?: string }>("/api/music/separate-stems", {
      method: "POST",
      body: JSON.stringify({ audio_path: audioPath })
    }),
  musicBrief: (payload: { prompt: string }) =>
    request<MusicBrief>("/api/music/brief", { method: "POST", body: JSON.stringify(payload) }),
  buildCalendar: (payload: { start_at: string; count: number; interval_minutes: number; platforms: string[] }) =>
    request<{ slots: CalendarSlot[] }>("/api/calendar/build", { method: "POST", body: JSON.stringify(payload) }),
  presetLibrary: () => request<PresetLibrary>("/api/preset-library"),
  installTemplatePreset: (presetId: string) =>
    request<Template>(`/api/preset-library/templates/${presetId}/install`, { method: "POST" }),
  exportPresets: () => request<ExportPreset[]>("/api/editor/export-presets"),
  assetProxies: async (assetId: string) =>
    (await request<AssetProxy[]>(`/api/editor/assets/${assetId}/proxies`)).map(normalizeProxy),
  generateAssetProxy: async (assetId: string) =>
    normalizeProxy(await request<AssetProxy>(`/api/editor/assets/${assetId}/proxy`, { method: "POST" })),
  sceneMarkers: (assetId: string) => request<SceneMarker[]>(`/api/editor/assets/${assetId}/markers`),
  createSceneMarker: (assetId: string, payload: {
    time_seconds: number;
    duration_seconds?: number | null;
    label: string;
    color: string;
    marker_type: "note" | "hook" | "cut" | "scene" | "chapter";
    notes: string;
  }) =>
    request<SceneMarker>(`/api/editor/assets/${assetId}/markers`, { method: "POST", body: JSON.stringify(payload) }),
  detectScenes: (assetId: string, payload: { threshold: number; limit: number }) =>
    request<{ markers: SceneMarker[]; count: number }>(`/api/editor/assets/${assetId}/scene-detect`, {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  deleteSceneMarker: (markerId: string) =>
    request<Record<string, never>>(`/api/editor/markers/${markerId}`, { method: "DELETE" }),
  assets: async () => (await request<Asset[]>("/api/assets")).map(normalizeAsset),
  assetSmartBins: () => request<{ bins: AssetSmartBin[] }>("/api/assets/smart-bins"),
  deleteAssets: (assetIds: string[]) =>
    request<DeleteAssetsResult>("/api/assets/delete", {
      method: "POST",
      body: JSON.stringify({ asset_ids: assetIds })
    }),
  reindexAssets: (onlyAttention = true, forceThumbnail = false) =>
    request<AssetReindexResult>(`/api/assets/reindex?only_attention=${onlyAttention}&force_thumbnail=${forceThumbnail}`, {
      method: "POST"
    }),
  importAssets: async (paths: string[]) => {
    const result = await request<{ imported: Asset[]; count: number }>("/api/assets/import", {
      method: "POST",
      body: JSON.stringify({ paths, copy_to_library: true })
    });
    return { ...result, imported: result.imported.map(normalizeAsset) };
  },
  uploadAssets: async (files: FileList | File[]) => {
    const formData = new FormData();
    Array.from(files).forEach((file) => formData.append("files", file));
    const result = await request<{ imported: Asset[]; count: number }>("/api/assets/upload", {
      method: "POST",
      body: formData
    });
    return { ...result, imported: result.imported.map(normalizeAsset) };
  },
  templates: () => request<Template[]>("/api/templates"),
  getTemplate: (id: string) => request<Template>(`/api/templates/${id}`),
  createTemplate: (payload: { name: string; description: string; recipe: RenderRecipe }) =>
    request<Template>("/api/templates", { method: "POST", body: JSON.stringify(payload) }),
  updateTemplate: (id: string, payload: { name?: string; description?: string; recipe?: RenderRecipe }) =>
    request<Template>(`/api/templates/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteTemplate: (id: string) =>
    request<{ ok: boolean; id: string }>(`/api/templates/${id}`, { method: "DELETE" }),
  duplicateTemplate: (id: string, name?: string) =>
    request<Template>(`/api/templates/${id}/duplicate`, { method: "POST", body: JSON.stringify({ name }) }),
  batches: () => request<Batch[]>("/api/batches"),
  createBatch: (payload: {
    name: string;
    template_id: string;
    asset_ids: string[];
    variations: number;
    output_dir?: string | null;
    estimated_output_bytes?: number | null;
  }) =>
    request<Batch>("/api/batches", { method: "POST", body: JSON.stringify(payload) }),
  pauseBatch: (batchId: string) => request<Batch>(`/api/batches/${batchId}/pause`, { method: "POST" }),
  resumeBatch: (batchId: string) => request<Batch>(`/api/batches/${batchId}/resume`, { method: "POST" }),
  cancelBatch: (batchId: string) => request<Batch>(`/api/batches/${batchId}/cancel`, { method: "POST" }),
  retryBatch: (batchId: string, resetAttempts = false) =>
    request<Batch>(`/api/batches/${batchId}/retry`, {
      method: "POST",
      body: JSON.stringify({ reset_attempts: resetAttempts })
    }),
  jobs: () => request<RenderJob[]>("/api/jobs"),
  processNext: () => request<{ processed: RenderJob | null; message?: string }>("/api/jobs/process-next", { method: "POST" }),
  retryJob: (jobId: string) =>
    request<RenderJob>(`/api/jobs/${jobId}/retry`, {
      method: "POST",
      body: JSON.stringify({ reset_attempts: false })
    }),
  cancelJob: (jobId: string) => request<RenderJob>(`/api/jobs/${jobId}/cancel`, { method: "POST" }),
  renders: async () => (await request<RenderedVideo[]>("/api/renders")).map(normalizeRender),
  reviewRender: (id: string, status: RenderedVideo["status"]) =>
    request<RenderedVideo>(`/api/renders/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }),
  qualityCheckRender: (id: string, platforms: PlatformPreset["platform"][] = ["instagram_reels", "tiktok", "youtube_shorts"]) =>
    request<QualityCheckResult>(`/api/quality/renders/${id}`, {
      method: "POST",
      body: JSON.stringify({ platforms })
    }),
  analyzeBatchQuality: (batchId: string, platforms: PlatformPreset["platform"][] = ["instagram_reels", "tiktok", "youtube_shorts"]) =>
    request<BatchQualitySummary>(`/api/quality/batches/${batchId}`, {
      method: "POST",
      body: JSON.stringify({ platforms })
    }),
  getBatchQuality: (batchId: string) =>
    request<BatchQualitySummary>(`/api/quality/batches/${batchId}`),
  presets: () => request<PlatformPreset[]>("/api/platform-presets"),
  publishTasks: () => request<PublishTask[]>("/api/publish-tasks"),
  publishQualityReport: (id: string) =>
    request<PackageQualityReport>(`/api/publish-tasks/${id}/quality-report`),
  publishQualityReportUrl: (id: string) => `${API_BASE}/api/publish-tasks/${id}/quality-report`,
  createPublishPackage: (payload: {
    rendered_video_ids: string[];
    platforms: PlatformPreset["platform"][];
    caption: string;
    hashtags: string[];
    output_dir?: string;
  }) =>
    request<{ created: PublishTask[]; count: number }>("/api/publish-packages", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  updatePublishTask: (id: string, status: PublishTask["status"]) =>
    request<PublishTask>(`/api/publish-tasks/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }),
  checkAssetIntegrity: (assetId: string) =>
    request<IntegrityCheckResult>(`/api/quality/assets/${assetId}/integrity`, { method: "POST" }),
  checkRenderIntegrity: (renderedId: string) =>
    request<IntegrityCheckResult>(`/api/quality/renders/${renderedId}/integrity`, { method: "POST" }),
  settings: () => request<SystemSettings>("/api/system/settings"),
  updateSettings: (payload: SettingsUpdateRequest) =>
    request<SystemSettings>("/api/system/settings", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  resetSettings: () =>
    request<SystemSettings>("/api/system/settings/reset", {
      method: "POST"
    }),
  openPath: (path: string) =>
    request<{ success: boolean; opened_path: string }>("/api/system/open-path", {
      method: "POST",
      body: JSON.stringify({ path })
    }),
  calendarSlots: () => request<CalendarSlot[]>("/api/calendar/slots"),
  createCalendarSlot: (payload: Partial<CalendarSlot>) =>
    request<CalendarSlot>("/api/calendar/slots", { method: "POST", body: JSON.stringify(payload) }),
  generateWeeklySlots: (payload?: Record<string, unknown>) =>
    request<{ slots: CalendarSlot[]; count: number }>("/api/calendar/generate-week", { method: "POST", body: JSON.stringify(payload || {}) }),
  updateCalendarSlot: (slotId: string, payload: Partial<CalendarSlot>) =>
    request<CalendarSlot>(`/api/calendar/slots/${slotId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteCalendarSlot: (slotId: string) =>
    request<{ ok: boolean }>(`/api/calendar/slots/${slotId}`, { method: "DELETE" }),
  updatePublishTaskChecklist: (id: string, checklist: string[]) =>
    request<PublishTask>(`/api/publish-tasks/${id}/checklist`, {
      method: "PATCH",
      body: JSON.stringify({ checklist })
    }),
  openPublishTaskFolder: (id: string) =>
    request<{ status: string; package_dir: string }>(`/api/publish-tasks/${id}/open-folder`, {
      method: "POST"
    }),
  viralHooks: (topic: string) =>
    request<{ topic: string; hooks: ViralHook[] }>("/api/agents/viral-hooks", {
      method: "POST",
      body: JSON.stringify({ topic })
    }),
  scriptToVideo: (topic: string) =>
    request<{ title: string; target_duration: string; blocks: ScriptBlock[] }>("/api/agents/script-to-video", {
      method: "POST",
      body: JSON.stringify({ topic })
    }),
  autopilot: (payload: { name?: string; asset_id?: string; template_id?: string; variations?: number }) =>
    request<AutopilotResult>("/api/agents/autopilot", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  getAiStatus: () => request<AiProvidersStatus>("/api/system/ai-status"),
  testGoogleApi: (payload?: string | { api_key?: string; model?: string }) => {
    const body = typeof payload === "string" ? { api_key: payload } : (payload || {});
    return request<{ available: boolean; model?: string; error?: string }>("/api/system/test-google-api", {
      method: "POST",
      body: JSON.stringify(body)
    });
  },
  getTtsVoices: () => request<TtsVoice[]>("/api/system/tts/voices"),
  synthesizeSpeech: (payload: { text: string; voice?: string }) =>
    request<TtsSynthesizeResult>("/api/system/tts/synthesize", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  mineViralClips: (assetId: string, payload?: { min_seconds?: number; max_seconds?: number; target_count?: number }) =>
    request<MinedClipsResponse>(`/api/clips/assets/${assetId}/mine-viral`, {
      method: "POST",
      body: JSON.stringify(payload || {})
    }),
  getAssetClips: (assetId: string) =>
    request<MinedClip[]>(`/api/clips/assets/${assetId}`),
  createBatchFromClips: (payload: {
    asset_id: string;
    template_id: string;
    clips: MinedClip[];
    batch_name?: string;
    enable_captions?: boolean;
    caption_style?: string;
    enable_music?: boolean;
    music_volume?: number;
    enable_jumpcut?: boolean;
  }) =>
    request<Batch>("/api/clips/batch-create", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  generateScriptToVideo: (topic: string) =>
    request<GeneratedScriptResponse>("/api/agents/script-to-video", {
      method: "POST",
      body: JSON.stringify({ topic })
    }),
  generateFacelessVideo: (payload: GenerateFacelessVideoPayload) =>
    request<GenerateFacelessVideoResponse>("/api/agents/generate-faceless-video", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  generateSceneImage: (payload: GenerateSceneImagePayload) =>
    request<GenerateSceneImageResponse>("/api/agents/generate-scene-image", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  runAutopilotPipeline: (payload: AutopilotPipelinePayload) =>
    request<AutopilotPipelineResponse>("/api/clips/autopilot", {
      method: "POST",
      body: JSON.stringify(payload)
    })
};

