const WORKSPACE_PREFIX = "/workspace/";
const MASSLOADER_PREFIX = "data/incoming/massloader";

export function toLocalMassloaderPath(path: string | null | undefined) {
  const normalized = (path ?? "").trim().replace(/\\/g, "/");
  if (!normalized.startsWith(WORKSPACE_PREFIX)) return null;

  const relativePath = normalized.slice(WORKSPACE_PREFIX.length);
  if (!relativePath.startsWith(MASSLOADER_PREFIX)) return null;

  return relativePath.split("/").join("\\");
}
