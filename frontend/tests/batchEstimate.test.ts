import {
  canCreateEstimatedBatch,
  estimateBatchCost,
  formatEstimateBytes,
  formatEstimateDuration,
  resolutionProfile
} from "../src/batchEstimate";

function expectEqual(actual: unknown, expected: unknown, label: string) {
  if (actual !== expected) {
    throw new Error(`${label}: expected ${String(expected)}, received ${String(actual)}`);
  }
}

const estimate1080 = estimateBatchCost({
  durations: [10, 20],
  variations: 2,
  width: 1080,
  height: 1920
});
expectEqual(estimate1080.profile.id, "1080p", "1080p profile");
expectEqual(estimate1080.totalJobs, 4, "job count");
expectEqual(estimate1080.renderedDurationSeconds, 60, "rendered duration");
expectEqual(Math.round(estimate1080.estimatedWallSeconds), 96, "estimated wall time");
expectEqual(Math.round(estimate1080.estimatedOutputBytes), 42_590_720, "estimated output size");
expectEqual(estimate1080.requires4kConfirmation, false, "1080p does not require confirmation");

const estimateUnknown = estimateBatchCost({ durations: [null], variations: 1, width: 1440, height: 2560 });
expectEqual(estimateUnknown.profile.id, "2k", "2K profile");
expectEqual(estimateUnknown.renderedDurationSeconds, 30, "unknown duration fallback");
expectEqual(estimateUnknown.unknownDurationCount, 1, "unknown duration count");

const extensive4k = estimateBatchCost({ durations: [10, 10], variations: 1, width: 2160, height: 3840 });
expectEqual(extensive4k.profile.id, "4k", "4K profile");
expectEqual(extensive4k.requires4kConfirmation, true, "extensive 4K confirmation");
expectEqual(extensive4k.peakMemoryBytes, 5_133_721_600, "4K peak memory");
expectEqual(canCreateEstimatedBatch(true, extensive4k, false), false, "unconfirmed extensive 4K is blocked");
expectEqual(canCreateEstimatedBatch(true, extensive4k, true), true, "confirmed extensive 4K is allowed");
expectEqual(canCreateEstimatedBatch(false, estimate1080, true), false, "missing selection is blocked");
expectEqual(canCreateEstimatedBatch(true, estimate1080, true, false), false, "insufficient storage is blocked");
expectEqual(canCreateEstimatedBatch(true, estimate1080, true, null), true, "unknown storage does not false-block");

const short4k = estimateBatchCost({ durations: [20], variations: 1, width: 2160, height: 3840 });
expectEqual(short4k.requires4kConfirmation, false, "short 4K does not require confirmation");

const trimmed = estimateBatchCost({
  durations: [20],
  variations: 2,
  width: 1080,
  height: 1920,
  trim: { start: 2, end: 5 }
});
expectEqual(trimmed.renderedDurationSeconds, 6, "trimmed duration is used for every variation");

const boundedUnknown = estimateBatchCost({
  durations: [null],
  variations: 1,
  width: 1080,
  height: 1920,
  trim: { start: 2, end: 5 }
});
expectEqual(boundedUnknown.renderedDurationSeconds, 3, "bounded trim replaces unknown duration fallback");
expectEqual(boundedUnknown.unknownDurationCount, 0, "bounded trim is not reported as unknown");

const localHistory = {
  minimum_samples: 3,
  profiles: [
    {
      template_id: "template-local",
      resolution: "1080p" as const,
      sample_count: 3,
      wall_seconds_per_output_second: 2,
      bytes_per_output_second: 100,
      memory_sample_count: 2,
      peak_memory_bytes: 2_000_000_000
    }
  ]
};
const calibrated = estimateBatchCost({
  durations: [10],
  variations: 1,
  width: 1080,
  height: 1920,
  templateId: "template-local",
  history: localHistory
});
expectEqual(calibrated.calibrationSource, "local_history", "eligible local history is used");
expectEqual(calibrated.estimatedWallSeconds, 20, "local wall ratio");
expectEqual(calibrated.estimatedOutputBytes, 1000, "local byte ratio");
expectEqual(calibrated.peakMemoryBytes, 2_000_000_000, "higher local peak raises the memory estimate");
expectEqual(calibrated.memoryCalibrationSource, "local_history", "valid local peak is exposed");
expectEqual(calibrated.memoryCalibrationSampleCount, 2, "memory sample count is exposed");

const insufficientHistory = estimateBatchCost({
  durations: [10],
  variations: 1,
  width: 1080,
  height: 1920,
  templateId: "template-local",
  history: { ...localHistory, profiles: [{ ...localHistory.profiles[0], sample_count: 2 }] }
});
expectEqual(insufficientHistory.calibrationSource, "benchmark", "small local sample keeps benchmark fallback");
expectEqual(insufficientHistory.calibrationSampleCount, 2, "calibration progress is exposed");

const lowerLocalMemory = estimateBatchCost({
  durations: [10],
  variations: 1,
  width: 1080,
  height: 1920,
  templateId: "template-local",
  history: {
    ...localHistory,
    profiles: [{ ...localHistory.profiles[0], memory_sample_count: 1, peak_memory_bytes: 100_000_000 }]
  }
});
expectEqual(lowerLocalMemory.peakMemoryBytes, 1_621_065_728, "local memory never lowers the benchmark floor");
expectEqual(lowerLocalMemory.memoryCalibrationSource, "local_history", "lower observed memory is still identified");

expectEqual(resolutionProfile(1080, 1920).label, "1080p", "resolution label");
expectEqual(formatEstimateDuration(96), "1m 36s", "duration formatting");
expectEqual(formatEstimateBytes(2_129_536), "2.0 MiB", "byte formatting");

console.log("batch estimate helper ok");
