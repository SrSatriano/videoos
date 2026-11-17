import { toLocalMassloaderPath } from "../src/massloaderPaths";

function expectEqual(actual: unknown, expected: unknown, label: string) {
  if (actual !== expected) {
    throw new Error(`${label}: expected ${String(expected)}, received ${String(actual)}`);
  }
}

expectEqual(
  toLocalMassloaderPath("/workspace/data/incoming/massloader/20260619-234104"),
  "data\\incoming\\massloader\\20260619-234104",
  "container path maps to local project path"
);

expectEqual(
  toLocalMassloaderPath("\\workspace\\data\\incoming\\massloader\\20260619-234104"),
  "data\\incoming\\massloader\\20260619-234104",
  "windows-like container path is normalized"
);

expectEqual(
  toLocalMassloaderPath("/workspace/data/assets/video.mp4"),
  null,
  "non-massloader workspace path is not rewritten"
);

expectEqual(toLocalMassloaderPath(""), null, "empty path is ignored");

console.log("massloader path helper ok");
