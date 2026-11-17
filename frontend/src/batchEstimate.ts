export type ResolutionProfileId = "1080p" | "2k" | "4k";

export interface BatchEstimateHistoryProfile {
  template_id: string;
  resolution: ResolutionProfileId;
  sample_count: number;
  wall_seconds_per_output_second: number;
  bytes_per_output_second: number;
  memory_sample_count: number;
  peak_memory_bytes: number | null;
}

export interface BatchEstimateHistory {
  minimum_samples: number;
  profiles: BatchEstimateHistoryProfile[];
}

interface ResolutionProfile {
  id: ResolutionProfileId;
  label: string;
  wallSecondsPerSourceSecond: number;
  bytesPerSourceSecond: number;
  peakMemoryBytes: number;
}

export interface BatchCostEstimate {
  profile: ResolutionProfile;
  totalJobs: number;
  renderedDurationSeconds: number;
  estimatedWallSeconds: number;
  estimatedOutputBytes: number;
  peakMemoryBytes: number;
  unknownDurationCount: number;
  requires4kConfirmation: boolean;
  calibrationSource: "benchmark" | "local_history";
  calibrationSampleCount: number;
  memoryCalibrationSource: "benchmark" | "local_history";
  memoryCalibrationSampleCount: number;
  minimumCalibrationSamples: number;
}

interface BatchCostInput {
  durations: Array<number | null | undefined>;
  variations: number;
  width: number;
  height: number;
  templateId?: string;
  trim?: { start?: number | null; end?: number | null };
  history?: BatchEstimateHistory;
}

const UNKNOWN_DURATION_FALLBACK_SECONDS = 30;

// Passada 22: same 3-second framed recipe, sequential libx264 renders.
const PROFILES: Record<ResolutionProfileId, ResolutionProfile> = {
  "1080p": {
    id: "1080p",
    label: "1080p",
    wallSecondsPerSourceSecond: 4.822 / 3,
    bytesPerSourceSecond: 2_129_536 / 3,
    peakMemoryBytes: 1_621_065_728
  },
  "2k": {
    id: "2k",
    label: "2K",
    wallSecondsPerSourceSecond: 6.731 / 3,
    bytesPerSourceSecond: 4_151_313 / 3,
    peakMemoryBytes: 2_515_910_656
  },
  "4k": {
    id: "4k",
    label: "4K",
    wallSecondsPerSourceSecond: 14.168 / 3,
    bytesPerSourceSecond: 8_598_964 / 3,
    peakMemoryBytes: 5_133_721_600
  }
};

export function resolutionProfile(width: number, height: number): ResolutionProfile {
  if (width >= 2160 || height >= 3840) return PROFILES["4k"];
  if (width >= 1440 || height >= 2560) return PROFILES["2k"];
  return PROFILES["1080p"];
}

function finiteNonNegative(value: number | null | undefined, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : fallback;
}

function effectiveDuration(
  duration: number | null | undefined,
  trim: BatchCostInput["trim"]
): { seconds: number; unknown: boolean } {
  const sourceSeconds = typeof duration === "number" && Number.isFinite(duration) && duration > 0 ? duration : null;
  const start = finiteNonNegative(trim?.start, 0);
  const configuredEnd = finiteNonNegative(trim?.end, 0);
  const end = configuredEnd > start ? configuredEnd : null;

  if (sourceSeconds !== null) {
    const effectiveEnd = end === null ? sourceSeconds : Math.min(end, sourceSeconds);
    return { seconds: Math.max(1, effectiveEnd - Math.min(start, effectiveEnd)), unknown: false };
  }
  if (end !== null) {
    return { seconds: end - start, unknown: false };
  }
  return { seconds: UNKNOWN_DURATION_FALLBACK_SECONDS, unknown: true };
}

export function estimateBatchCost(input: BatchCostInput): BatchCostEstimate {
  const profile = resolutionProfile(input.width, input.height);
  const variations = Number.isFinite(input.variations) ? Math.max(1, Math.floor(input.variations)) : 1;
  const effectiveDurations = input.durations.map((duration) => effectiveDuration(duration, input.trim));
  const unknownDurationCount = effectiveDurations.filter((item) => item.unknown).length;
  const selectedDurationSeconds = effectiveDurations.reduce((total, item) => total + item.seconds, 0);
  const renderedDurationSeconds = selectedDurationSeconds * variations;
  const totalJobs = input.durations.length * variations;
  const requires4kConfirmation =
    profile.id === "4k" && (totalJobs > 1 || renderedDurationSeconds > UNKNOWN_DURATION_FALLBACK_SECONDS);
  const minimumCalibrationSamples = Math.max(1, Math.floor(input.history?.minimum_samples ?? 3));
  const historyProfile = input.history?.profiles.find(
    (item) => item.template_id === input.templateId && item.resolution === profile.id
  );
  const usesLocalHistory = Boolean(
    historyProfile &&
      historyProfile.sample_count >= minimumCalibrationSamples &&
      Number.isFinite(historyProfile.wall_seconds_per_output_second) &&
      historyProfile.wall_seconds_per_output_second > 0 &&
      Number.isFinite(historyProfile.bytes_per_output_second) &&
      historyProfile.bytes_per_output_second > 0
  );
  const wallSecondsPerOutputSecond = usesLocalHistory
    ? historyProfile!.wall_seconds_per_output_second
    : profile.wallSecondsPerSourceSecond;
  const bytesPerOutputSecond = usesLocalHistory
    ? historyProfile!.bytes_per_output_second
    : profile.bytesPerSourceSecond;
  const usesLocalMemory = Boolean(
    historyProfile &&
      historyProfile.memory_sample_count > 0 &&
      typeof historyProfile.peak_memory_bytes === "number" &&
      Number.isFinite(historyProfile.peak_memory_bytes) &&
      historyProfile.peak_memory_bytes > 0
  );
  const peakMemoryBytes = usesLocalMemory
    ? Math.max(profile.peakMemoryBytes, historyProfile!.peak_memory_bytes!)
    : profile.peakMemoryBytes;

  return {
    profile,
    totalJobs,
    renderedDurationSeconds,
    estimatedWallSeconds: renderedDurationSeconds * wallSecondsPerOutputSecond,
    estimatedOutputBytes: renderedDurationSeconds * bytesPerOutputSecond,
    peakMemoryBytes,
    unknownDurationCount,
    requires4kConfirmation,
    calibrationSource: usesLocalHistory ? "local_history" : "benchmark",
    calibrationSampleCount: historyProfile?.sample_count ?? 0,
    memoryCalibrationSource: usesLocalMemory ? "local_history" : "benchmark",
    memoryCalibrationSampleCount: historyProfile?.memory_sample_count ?? 0,
    minimumCalibrationSamples
  };
}

export function canCreateEstimatedBatch(
  hasRequiredSelection: boolean,
  estimate: BatchCostEstimate | null,
  fourKConfirmed: boolean,
  hasStorageCapacity: boolean | null = null
): boolean {
  if (!hasRequiredSelection) return false;
  if (hasStorageCapacity === false) return false;
  return !estimate?.requires4kConfirmation || fourKConfirmed;
}

export function formatEstimateDuration(seconds: number): string {
  const rounded = Math.max(0, Math.round(seconds));
  if (rounded < 60) return `${rounded}s`;
  const hours = Math.floor(rounded / 3600);
  const minutes = Math.floor((rounded % 3600) / 60);
  const remainingSeconds = rounded % 60;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m ${remainingSeconds}s`;
}

export function formatEstimateBytes(bytes: number): string {
  const mib = bytes / 1024 / 1024;
  if (mib < 1024) return `${mib.toFixed(mib >= 100 ? 0 : 1)} MiB`;
  return `${(mib / 1024).toFixed(2)} GiB`;
}
