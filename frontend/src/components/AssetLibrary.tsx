import { CheckCircle2, Filter, FolderInput, LayoutGrid, List, Pencil, RefreshCw, Sparkles, Trash2, TriangleAlert } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { api } from "../api";
import type { Asset, AssetSmartBin, IntegrityCheckResult } from "../types";

function formatDuration(seconds: number | null): string {
  if (!seconds) return "--";
  const minutes = Math.floor(seconds / 60);
  const remaining = Math.round(seconds % 60).toString().padStart(2, "0");
  return `${minutes}:${remaining}`;
}

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

interface AssetLibraryProps {
  assets: Asset[];
  selectedAssetIds: string[];
  importPath: string;
  onImportPathChange: (value: string) => void;
  onImport: () => void;
  onImportPaths: (paths: string[]) => void;
  onUpload: (files: FileList | File[]) => void;
  onToggleAsset: (assetId: string) => void;
  onSelectAssets: (assetIds: string[]) => void;
  onDeleteAssets: (assetIds: string[]) => void;
  onEditSelected: () => void;
  onRefresh: () => void;
  onOpenClips?: (assetId: string) => void;
}

export function AssetLibrary({
  assets,
  selectedAssetIds,
  importPath,
  onImportPathChange,
  onImport,
  onImportPaths,
  onUpload,
  onToggleAsset,
  onSelectAssets,
  onDeleteAssets,
  onEditSelected,
  onRefresh,
  onOpenClips
}: AssetLibraryProps) {
  const [query, setQuery] = useState("");
  const [smartBins, setSmartBins] = useState<AssetSmartBin[]>([]);
  const [activeBin, setActiveBin] = useState("all");
  const [viewMode, setViewMode] = useState<"list" | "grid">("list");
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const folderInputRef = useRef<HTMLInputElement | null>(null);
  const [integrityResults, setIntegrityResults] = useState<Record<string, IntegrityCheckResult & { loading?: boolean }>>({});
  const [repairingAssets, setRepairingAssets] = useState(false);
  const [repairMessage, setRepairMessage] = useState("");

  const refreshSmartBins = async () => {
    try {
      const result = await api.assetSmartBins();
      setSmartBins(result.bins);
    } catch {
      setSmartBins([]);
    }
  };

  const checkAsset = async (assetId: string, event?: React.MouseEvent) => {
    if (event) {
      event.stopPropagation();
    }
    setIntegrityResults(prev => ({
      ...prev,
      [assetId]: { loading: true, valid: false, error_type: null, message: "Verificando..." }
    }));
    try {
      const res = await api.checkAssetIntegrity(assetId);
      setIntegrityResults(prev => ({ ...prev, [assetId]: res }));
    } catch (error: any) {
      setIntegrityResults(prev => ({
        ...prev,
        [assetId]: {
          valid: false,
          error_type: "check_timeout_or_failed",
          message: error.message || "Erro desconhecido ao checar integridade."
        }
      }));
    }
  };

  useEffect(() => {
    folderInputRef.current?.setAttribute("webkitdirectory", "true");
    folderInputRef.current?.setAttribute("directory", "true");
  }, []);
  useEffect(() => {
    void refreshSmartBins();
  }, [assets.length]);

  const reindexAttentionAssets = async () => {
    setRepairingAssets(true);
    setRepairMessage("");
    try {
      const result = await api.reindexAssets(true, false);
      setRepairMessage(`Reindexacao: ${result.repaired}/${result.checked} reparados; ${result.failed} falhas; ${result.skipped} ignorados.`);
      await refreshSmartBins();
      onRefresh();
    } catch (error: any) {
      setRepairMessage(error.message || "Falha ao reindexar assets.");
    } finally {
      setRepairingAssets(false);
    }
  };
  const filteredAssets = useMemo(
    () => {
      const bin = smartBins.find((item) => item.id === activeBin);
      const allowedIds = bin && bin.id !== "all" ? new Set(bin.asset_ids) : null;
      return assets.filter((asset) => {
        const matchesQuery = asset.filename.toLowerCase().includes(query.toLowerCase());
        const matchesBin = allowedIds ? allowedIds.has(asset.id) : true;
        return matchesQuery && matchesBin;
      });
    },
    [activeBin, assets, query, smartBins]
  );
  const activeSmartBin = smartBins.find((item) => item.id === activeBin);
  const currentBinAssetIds = filteredAssets.map((asset) => asset.id);

  const exploreFiles = async () => {
    if (window.videoOS?.isDesktop) {
      const paths = await window.videoOS.pickFiles();
      if (paths.length) onImportPaths(paths);
      return;
    }
    fileInputRef.current?.click();
  };

  const exploreFolder = async () => {
    if (window.videoOS?.isDesktop) {
      const path = await window.videoOS.pickFolder();
      if (path) onImportPaths([path]);
      return;
    }
    folderInputRef.current?.click();
  };

  return (
    <section className="view-grid two-column">
      <div className="panel library-panel">
        <div className="panel-heading">
          <div>
            <h2>Biblioteca</h2>
            <p>{assets.length} videos rastreados no banco local.</p>
          </div>
          <button className="icon-button" onClick={onRefresh} type="button" title="Atualizar">
            <RefreshCw size={17} />
          </button>
        </div>

        <div className="inline-form">
          <FolderInput size={18} />
          <input
            value={importPath}
            onChange={(event) => onImportPathChange(event.target.value)}
            placeholder="Caminho da pasta ou arquivo"
          />
          <button className="primary-button compact" onClick={onImport} type="button">
            Importar caminho
          </button>
        </div>
        <div className="command-actions left">
          <input
            ref={fileInputRef}
            hidden
            multiple
            accept="video/*,.mp4,.mov,.m4v,.webm,.mkv"
            type="file"
            onChange={(event) => event.target.files && onUpload(event.target.files)}
          />
          <input
            ref={folderInputRef}
            hidden
            multiple
            accept="video/*,.mp4,.mov,.m4v,.webm,.mkv"
            type="file"
            onChange={(event) => event.target.files && onUpload(event.target.files)}
          />
          <button className="secondary-button compact" onClick={exploreFiles} type="button">
            Explorar arquivos
          </button>
          <button className="secondary-button compact" onClick={exploreFolder} type="button">
            Explorar pasta
          </button>
          <button className="secondary-button compact" disabled={repairingAssets} onClick={reindexAttentionAssets} type="button">
            <RefreshCw size={14} />
            {repairingAssets ? "Reindexando..." : "Reindexar atencao"}
          </button>
        </div>
        {repairMessage ? <p className="bin-hint">{repairMessage}</p> : null}

        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <input
            className="search-input"
            style={{ flex: 1, margin: 0 }}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Filtrar por nome"
          />
          <div style={{ display: "flex", gap: "0.25rem" }}>
            <button
              className={`secondary-button compact ${viewMode === "list" ? "active" : ""}`}
              onClick={() => setViewMode("list")}
              title="Visualizar em Lista"
              type="button"
              style={{ padding: "0.45rem" }}
            >
              <List size={14} />
            </button>
            <button
              className={`secondary-button compact ${viewMode === "grid" ? "active" : ""}`}
              onClick={() => setViewMode("grid")}
              title="Visualizar em Grade"
              type="button"
              style={{ padding: "0.45rem" }}
            >
              <LayoutGrid size={14} />
            </button>
          </div>
        </div>
        <div className="smart-bin-strip" aria-label="Smart bins">
          {(smartBins.length ? smartBins : [{ id: "all", label: "Todos", description: "", count: assets.length, asset_ids: assets.map((asset) => asset.id) }]).map((bin) => (
            <button
              className={activeBin === bin.id ? "smart-bin active" : "smart-bin"}
              key={bin.id}
              onClick={() => setActiveBin(bin.id)}
              title={bin.description}
              type="button"
            >
              <Filter size={14} />
              <span>{bin.label}</span>
              <strong>{bin.count}</strong>
            </button>
          ))}
        </div>

        <div
          className="asset-list"
          style={
            viewMode === "grid"
              ? {
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
                  gap: "0.75rem",
                  maxHeight: "none",
                }
              : undefined
          }
        >
          {filteredAssets.map((asset) => {
            const selected = selectedAssetIds.includes(asset.id);
            return (
              <article
                className={selected ? "asset-row selected" : "asset-row"}
                key={asset.id}
              >
                <button
                  className="asset-select-main"
                  type="button"
                  onClick={() => onToggleAsset(asset.id)}
                  aria-pressed={selected}
                >
                  <div className="thumb-frame">
                    {asset.thumbnail_url ? <img src={asset.thumbnail_url} alt="" /> : <FilePlaceholder />}
                  </div>
                  <div className="asset-meta">
                    <strong>{asset.filename}</strong>
                    <span>
                      {asset.orientation} · {formatDuration(asset.duration_seconds)} · {formatSize(asset.size_bytes)}
                    </span>
                  </div>
                  <span className="asset-resolution">
                    {asset.width && asset.height ? `${asset.width}x${asset.height}` : asset.metadata_status}
                  </span>
                </button>

                <div className="asset-meta-integrity">
                  {(() => {
                    const integrity = integrityResults[asset.id];
                    if (integrity) {
                      if (integrity.loading) {
                        return (
                          <span className="integrity-loading" title="Verificando integridade física...">
                            <RefreshCw size={14} className="animate-spin" />
                          </span>
                        );
                      }
                      return (
                        <button
                          className={`integrity-status-btn ${integrity.valid ? "valid" : "invalid"}`}
                          onClick={(e) => checkAsset(asset.id, e)}
                          title={`${integrity.message}${integrity.fix ? ' | Correção: ' + integrity.fix : ''}`}
                          type="button"
                        >
                          {integrity.valid ? <CheckCircle2 size={13} /> : <TriangleAlert size={13} />}
                          {integrity.valid ? "Íntegro" : integrity.error_type === "file_missing" ? "Ausente" : "Corrompido"}
                        </button>
                      );
                    }
                    return (
                      <button
                        className="integrity-audit-btn"
                        onClick={(e) => checkAsset(asset.id, e)}
                        title="Auditar integridade física do arquivo"
                        type="button"
                      >
                        Auditar
                      </button>
                    );
                  })()}
                </div>

                <button
                  className="icon-button asset-delete-btn"
                  onClick={(event) => {
                    event.stopPropagation();
                    onDeleteAssets([asset.id]);
                  }}
                  title="Remover este video da biblioteca"
                  type="button"
                >
                  <Trash2 size={16} />
                </button>
              </article>
            );
          })}
          {filteredAssets.length === 0 ? (
            <div className="empty-state">Nenhum video importado ainda. Comece pela pasta Planejamento.</div>
          ) : null}
        </div>
      </div>

      <aside className="panel inspector-panel">
        <h2>Selecao do lote</h2>
        <p>Escolha um ou mais videos para renderizar com o template ativo.</p>
        <div className="selection-count">
          <strong>{selectedAssetIds.length}</strong>
          <span>assets selecionados</span>
        </div>
        <div className="command-actions left">
          <button className="secondary-button compact" onClick={() => onSelectAssets(currentBinAssetIds)} type="button">
            Selecionar bin
          </button>
          <button className="secondary-button compact" onClick={() => onSelectAssets([])} type="button">
            Limpar
          </button>
        </div>
        <div className="command-actions left">
          <button
            className="primary-button compact"
            disabled={selectedAssetIds.length === 0}
            onClick={onEditSelected}
            type="button"
          >
            <Pencil size={14} />
            Editar selecionados ({selectedAssetIds.length})
          </button>
          <button
            className="danger-button compact"
            disabled={selectedAssetIds.length === 0}
            onClick={() => onDeleteAssets(selectedAssetIds)}
            type="button"
          >
            <Trash2 size={14} />
            Excluir selecionados ({selectedAssetIds.length})
          </button>
        </div>
        {activeSmartBin ? <p className="bin-hint">{activeSmartBin.description}</p> : null}
        <div className="rule-list">
          <span>9:16 vertical</span>
          <span>H.264/AAC</span>
          <span>Thumb gerada</span>
          <span>Sem publicacao automatica</span>
        </div>

        {selectedAssetIds.length === 1 && (
          (() => {
            const asset = assets.find(a => a.id === selectedAssetIds[0]);
            if (!asset) return null;
            const integrity = integrityResults[asset.id];
            return (
              <div className="inspector-asset-detail">
                <h3>Detalhes do Vídeo</h3>
                <div className="inspector-detail-row">
                  <strong>Nome:</strong> <span title={asset.filename}>{asset.filename}</span>
                </div>
                <div className="inspector-detail-row">
                  <strong>Orientação:</strong> <span>{asset.orientation}</span>
                </div>
                <div className="inspector-detail-row">
                  <strong>Caminho:</strong> <span className="path-text" title={asset.stored_path}>{asset.stored_path}</span>
                </div>
                
                <div className="integrity-inspector-section">
                  <h4>Integridade Física</h4>
                  {integrity ? (
                    integrity.loading ? (
                      <p className="integrity-checking">Verificando decodificabilidade...</p>
                    ) : (
                      <div className={`integrity-result-card ${integrity.valid ? "valid" : "corrupt"}`}>
                        <strong>Status: {integrity.valid ? "Válido" : "Erro / Falha"}</strong>
                        <p>{integrity.message}</p>
                        {integrity.fix && <p className="fix-tip"><strong>Dica:</strong> {integrity.fix}</p>}
                        <button className="secondary-button compact" onClick={(e) => checkAsset(asset.id, e)} type="button">
                          Reavaliar
                        </button>
                      </div>
                    )
                  ) : (
                    <button className="primary-button compact" onClick={(e) => checkAsset(asset.id, e)} type="button">
                      Auditar Arquivo
                    </button>
                  )}
                </div>

                  <div className="ai-clips-inspector-section" style={{ marginTop: "1rem", paddingTop: "0.75rem", borderTop: "1px solid var(--line)" }}>
                    <h4 style={{ margin: "0 0 0.5rem 0", fontSize: "13px" }}>Automação & Cortes</h4>
                    <button
                      className="primary-button compact"
                      style={{ width: "100%", display: "flex", justifyContent: "center", alignItems: "center", gap: "6px" }}
                      onClick={() => onOpenClips?.(asset.id)}
                      type="button"
                    >
                      <Sparkles size={14} />
                      Minerar Cortes Virais (AI Clips)
                    </button>
                  </div>
                </div>
              );
            })()
          )}
      </aside>
    </section>
  );
}

function FilePlaceholder() {
  return (
    <div className="thumb-placeholder">
      <FolderInput size={22} />
    </div>
  );
}
