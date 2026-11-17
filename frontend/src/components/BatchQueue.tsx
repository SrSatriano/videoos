import {
  ArrowLeft,
  ArrowRight,
  Ban,
  Boxes,
  Check,
  CheckCircle2,
  ChevronDown,
  Clock3,
  Film,
  FolderOpen,
  HardDrive,
  Layers3,
  MemoryStick,
  Pause,
  Play,
  PlaySquare,
  RotateCcw,
  Search,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  Wand2,
  XCircle
} from "lucide-react";
import { useEffect, useState } from "react";

import {
  canCreateEstimatedBatch,
  estimateBatchCost,
  formatEstimateBytes,
  formatEstimateDuration
} from "../batchEstimate";
import { api } from "../api";
import { StatusPill } from "./StatusPill";
import { Button } from "./ui/Button";
import { SegmentedControl } from "./ui/SegmentedControl";
import type { Asset, Batch, BatchQualitySummary, RenderJob, RenderPerformanceSnapshot, StorageCapacityCheck, Template } from "../types";

interface BatchQueueProps {
  assets: Asset[];
  batches: Batch[];
  jobs: RenderJob[];
  renderPerformance?: RenderPerformanceSnapshot;
  templates: Template[];
  selectedAssetIds: string[];
  selectedTemplateId: string;
  onSelectAssets?: (assetIds: string[]) => void;
  onSelectTemplate?: (templateId: string) => void;
  variations: number;
  batchName: string;
  outputDir: string;
  onBatchNameChange: (value: string) => void;
  onOutputDirChange: (value: string) => void;
  onVariationsChange: (value: number) => void;
  onCreateBatch: (estimatedOutputBytes: number) => void | Promise<void>;
  onProcessNext: () => void | Promise<void>;
  onRetry: (jobId: string) => Promise<void>;
  onCancel: (jobId: string) => Promise<void>;
  onPauseBatch: (batchId: string) => Promise<void>;
  onResumeBatch: (batchId: string) => Promise<void>;
  onCancelBatch: (batchId: string) => Promise<void>;
  onRetryBatch: (batchId: string) => Promise<void>;
}

type JobFilter = "active" | "attention" | "all";

export function BatchQueue({
  assets,
  batches,
  jobs,
  renderPerformance,
  templates,
  selectedAssetIds,
  selectedTemplateId,
  onSelectAssets,
  onSelectTemplate,
  variations,
  batchName,
  outputDir,
  onBatchNameChange,
  onOutputDirChange,
  onVariationsChange,
  onCreateBatch,
  onProcessNext,
  onRetry,
  onCancel,
  onPauseBatch,
  onResumeBatch,
  onCancelBatch,
  onRetryBatch
}: BatchQueueProps) {
  const [wizardMode, setWizardMode] = useState(true);
  const [wizardStep, setWizardStep] = useState<1 | 2 | 3>(1);
  const [assetSearch, setAssetSearch] = useState("");
  const [fourKConfirmed, setFourKConfirmed] = useState(false);
  const [storageCheck, setStorageCheck] = useState<StorageCapacityCheck | null>(null);
  const [storageChecking, setStorageChecking] = useState(false);
  const [storageCheckError, setStorageCheckError] = useState<string | null>(null);
  const [jobFilter, setJobFilter] = useState<JobFilter>("active");
  const [visibleJobCount, setVisibleJobCount] = useState(50);
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [batchQcSummaries, setBatchQcSummaries] = useState<Record<string, BatchQualitySummary>>({});

  const handleRunBatchQc = async (batchId: string) => {
    await runAction(`qc-batch:${batchId}`, async () => {
      const summary = await api.analyzeBatchQuality(batchId);
      setBatchQcSummaries((prev) => ({ ...prev, [batchId]: summary }));
    });
  };
  const template = templates.find((item) => item.id === selectedTemplateId);
  const normalizedVariations = Number.isFinite(variations) ? Math.min(50, Math.max(1, Math.floor(variations))) : 1;
  const totalJobs = selectedAssetIds.length * normalizedVariations;
  const durationByAssetId = new Map(assets.map((asset) => [asset.id, asset.duration_seconds]));
  const selectedDurations = selectedAssetIds.map((assetId) => durationByAssetId.get(assetId));
  const estimate = template && selectedAssetIds.length > 0
    ? estimateBatchCost({
        durations: selectedDurations,
        variations: normalizedVariations,
        width: template.recipe.format.width,
        height: template.recipe.format.height,
        templateId: template.id,
        trim: template.recipe.trim,
        history: renderPerformance
      })
    : null;
  const estimateKey = `${selectedTemplateId}:${template?.recipe.format.width ?? 0}x${template?.recipe.format.height ?? 0}:${selectedDurations.join(",")}:${normalizedVariations}`;
  const activeJobs = jobs.filter((job) => job.status === "queued" || job.status === "processing").length;
  const attentionJobs = jobs.filter((job) => job.status === "failed" || job.status === "canceled").length;
  const filteredJobs = jobs.filter((job) => {
    if (jobFilter === "active") return job.status === "queued" || job.status === "processing";
    if (jobFilter === "attention") return job.status === "failed" || job.status === "canceled";
    return true;
  });
  const visibleJobs = filteredJobs.slice(0, visibleJobCount);
  const needs4kConfirmation = Boolean(estimate?.requires4kConfirmation);
  const canCreateBatch = canCreateEstimatedBatch(
    Boolean(template && selectedAssetIds.length > 0 && totalJobs > 0),
    estimate,
    fourKConfirmed,
    storageCheck?.has_capacity ?? null
  );

  useEffect(() => {
    setFourKConfirmed(false);
  }, [estimateKey]);

  useEffect(() => {
    setVisibleJobCount(50);
  }, [jobFilter]);

  useEffect(() => {
    let active = true;
    setStorageCheck(null);
    setStorageCheckError(null);
    if (!estimate) {
      setStorageChecking(false);
      return undefined;
    }

    const timeout = window.setTimeout(() => {
      setStorageChecking(true);
      api
        .checkStorage({ output_dir: outputDir || null, estimated_output_bytes: Math.ceil(estimate.estimatedOutputBytes) })
        .then((result) => {
          if (active) setStorageCheck(result);
        })
        .catch((error: unknown) => {
          if (active) setStorageCheckError(error instanceof Error ? error.message : "Falha ao verificar o disco.");
        })
        .finally(() => {
          if (active) setStorageChecking(false);
        });
    }, 250);

    return () => {
      active = false;
      window.clearTimeout(timeout);
    };
  }, [estimate?.estimatedOutputBytes, outputDir]);

  const pickOutputDir = async () => {
    const path = await window.videoOS?.pickFolder();
    if (path) {
      onOutputDirChange(path);
    }
  };

  const runAction = async (key: string, action: () => Promise<void>) => {
    setPendingAction(key);
    try {
      await action();
    } catch {
      // App exibe a mensagem de erro global; o controle local apenas libera a acao.
    } finally {
      setPendingAction(null);
    }
  };

  return (
    <section className="view-grid queue-layout">
      <div className="panel batch-create-panel">
        <div className="panel-heading">
          <div>
            <h2>{wizardMode ? "Batch Wizard (Criação Guiada)" : "Novo Lote (Modo Direto)"}</h2>
            <p>
              {selectedAssetIds.length} vídeos selecionados · {totalJobs} jobs · Template: {template?.name ?? "nenhum"}
            </p>
          </div>
          <div className="wizard-mode-toggle">
            <Button
              variant="ghost"
              compact
              icon={wizardMode ? <Layers3 size={15} /> : <Wand2 size={15} />}
              label={wizardMode ? "Modo Direto" : "Batch Wizard"}
              onClick={() => setWizardMode(!wizardMode)}
            />
            {!wizardMode && (
              <Button
                variant="primary"
                compact
                icon={<PlaySquare size={16} />}
                label="Criar fila"
                onClick={() => onCreateBatch(Math.ceil(estimate?.estimatedOutputBytes ?? 0))}
                disabled={!canCreateBatch}
              />
            )}
          </div>
        </div>

        {wizardMode ? (
          <div className="batch-wizard-flow">
            <div className="wizard-steps-indicator" aria-label="Passos do Wizard">
              <button
                type="button"
                className={`wizard-step-btn ${wizardStep === 1 ? "active" : ""} ${selectedAssetIds.length > 0 ? "completed" : ""}`}
                onClick={() => setWizardStep(1)}
              >
                <span className="step-num">1</span>
                <span className="step-text">Vídeos ({selectedAssetIds.length})</span>
              </button>
              <span className="step-divider">→</span>
              <button
                type="button"
                className={`wizard-step-btn ${wizardStep === 2 ? "active" : ""} ${selectedTemplateId ? "completed" : ""}`}
                onClick={() => setWizardStep(2)}
              >
                <span className="step-num">2</span>
                <span className="step-text">Template & Estilo</span>
              </button>
              <span className="step-divider">→</span>
              <button
                type="button"
                className={`wizard-step-btn ${wizardStep === 3 ? "active" : ""}`}
                onClick={() => setWizardStep(3)}
              >
                <span className="step-num">3</span>
                <span className="step-text">Pre-flight & Render</span>
              </button>
            </div>

            {wizardStep === 1 && (
              <div className="wizard-step-body wizard-step-1">
                <div className="wizard-filter-bar">
                  <div className="search-box">
                    <Search size={15} />
                    <input
                      placeholder="Filtrar vídeos por nome..."
                      value={assetSearch}
                      onChange={(e) => setAssetSearch(e.target.value)}
                    />
                  </div>
                  <div className="filter-actions">
                    <Button
                      variant="ghost"
                      compact
                      label={`Selecionar todos (${assets.filter((a) => a.filename.toLowerCase().includes(assetSearch.toLowerCase())).length})`}
                      onClick={() =>
                        onSelectAssets?.(
                          assets
                            .filter((a) => a.filename.toLowerCase().includes(assetSearch.toLowerCase()))
                            .map((a) => a.id)
                        )
                      }
                    />
                    <Button
                      variant="ghost"
                      compact
                      label="Limpar"
                      onClick={() => onSelectAssets?.([])}
                    />
                  </div>
                </div>

                <div className="wizard-asset-grid">
                  {assets
                    .filter((a) => a.filename.toLowerCase().includes(assetSearch.toLowerCase()))
                    .map((asset) => {
                      const isSelected = selectedAssetIds.includes(asset.id);
                      return (
                        <div
                          key={asset.id}
                          className={`wizard-asset-card ${isSelected ? "selected" : ""}`}
                          onClick={() => {
                            if (!onSelectAssets) return;
                            if (isSelected) {
                              onSelectAssets(selectedAssetIds.filter((id) => id !== asset.id));
                            } else {
                              onSelectAssets([...selectedAssetIds, asset.id]);
                            }
                          }}
                        >
                          <div className="asset-card-thumb">
                            <Film size={22} />
                            {isSelected && (
                              <span className="selection-badge">
                                <Check size={12} />
                              </span>
                            )}
                          </div>
                          <div className="asset-card-info">
                            <strong className="truncate">{asset.filename}</strong>
                            <div className="asset-card-pills">
                              <span>{asset.duration_seconds ? `${asset.duration_seconds.toFixed(0)}s` : "sem duração"}</span>
                              <span>{asset.width && asset.height ? `${asset.width}x${asset.height}` : "9:16"}</span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  {assets.filter((a) => a.filename.toLowerCase().includes(assetSearch.toLowerCase())).length === 0 && (
                    <div className="empty-state">Nenhum vídeo disponível no filtro.</div>
                  )}
                </div>

                <div className="wizard-footer-nav">
                  <span className="wizard-counter-note">
                    {selectedAssetIds.length} de {assets.length} vídeo(s) selecionado(s).
                  </span>
                  <Button
                    variant="primary"
                    icon={<ArrowRight size={16} />}
                    label="Avançar para Template"
                    disabled={selectedAssetIds.length === 0}
                    onClick={() => setWizardStep(2)}
                  />
                </div>
              </div>
            )}

            {wizardStep === 2 && (
              <div className="wizard-step-body wizard-step-2">
                <span className="wizard-section-subhead">Selecione o Template de Edição e Estilo Viral</span>
                <div className="wizard-template-grid">
                  {templates.map((tpl) => {
                    const isSelected = tpl.id === selectedTemplateId;
                    return (
                      <div
                        key={tpl.id}
                        className={`wizard-template-card ${isSelected ? "selected" : ""}`}
                        onClick={() => onSelectTemplate?.(tpl.id)}
                      >
                        <div className="template-card-top">
                          <strong>{tpl.name}</strong>
                          {isSelected && (
                            <span className="selection-badge">
                              <Check size={12} />
                            </span>
                          )}
                        </div>
                        <p>{tpl.description || "Preset de cortes, zoom inteligente e legendas virais."}</p>
                        <div className="template-card-tags">
                          <span className="tpl-tag">{tpl.recipe.format.width}x{tpl.recipe.format.height}</span>
                          <span className="tpl-tag">Punch-in 35%</span>
                          <span className="tpl-tag">Legendas ASS</span>
                          <span className="tpl-tag">Ducking DSP</span>
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div className="wizard-config-box">
                  <label>
                    Variações por vídeo (testes A/B)
                    <div className="variation-pill-row">
                      {[1, 2, 3, 5, 10].map((num) => (
                        <button
                          key={num}
                          type="button"
                          className={`pill-choice ${normalizedVariations === num ? "active" : ""}`}
                          onClick={() => onVariationsChange(num)}
                        >
                          {num}x {num === 1 ? "(Padrão)" : num === 3 ? "(A/B Test)" : ""}
                        </button>
                      ))}
                    </div>
                  </label>
                  <label>
                    Nome do lote
                    <input value={batchName} onChange={(event) => onBatchNameChange(event.target.value)} />
                  </label>
                  <label>
                    Pasta de exportação
                    <div className="path-input-row">
                      <input
                        value={outputDir}
                        onChange={(event) => onOutputDirChange(event.target.value)}
                        placeholder="data/renders ou pasta customizada"
                      />
                      {window.videoOS?.isDesktop ? (
                        <Button
                          variant="ghost"
                          className="icon-button"
                          onClick={pickOutputDir}
                          title="Escolher pasta"
                          icon={<FolderOpen size={16} />}
                        />
                      ) : null}
                    </div>
                  </label>
                </div>

                <div className="wizard-footer-nav">
                  <Button
                    variant="ghost"
                    icon={<ArrowLeft size={16} />}
                    label="Voltar para Vídeos"
                    onClick={() => setWizardStep(1)}
                  />
                  <Button
                    variant="primary"
                    icon={<ArrowRight size={16} />}
                    label="Avançar para Pre-Flight"
                    disabled={!selectedTemplateId}
                    onClick={() => setWizardStep(3)}
                  />
                </div>
              </div>
            )}

            {wizardStep === 3 && (
              <div className="wizard-step-body wizard-step-3">
                <div className="preflight-box">
                  <div className="preflight-head">
                    <Sparkles size={20} className="text-yellow" />
                    <div>
                      <strong>Pre-Flight Check do Lote</strong>
                      <span>Validação técnica local antes do início do processamento.</span>
                    </div>
                  </div>

                  <div className="preflight-metrics-grid">
                    <div>
                      <Boxes size={16} />
                      <span>Vídeos Fonte</span>
                      <strong>{selectedAssetIds.length}</strong>
                    </div>
                    <div>
                      <Layers3 size={16} />
                      <span>Variações</span>
                      <strong>{normalizedVariations}x</strong>
                    </div>
                    <div>
                      <PlaySquare size={16} />
                      <span>Total de Jobs</span>
                      <strong>{totalJobs}</strong>
                    </div>
                    <div>
                      <Clock3 size={16} />
                      <span>Tempo Estimado</span>
                      <strong>{estimate ? `~${formatEstimateDuration(estimate.estimatedWallSeconds)}` : "calculando..."}</strong>
                    </div>
                    <div>
                      <HardDrive size={16} />
                      <span>Saída Total</span>
                      <strong>{estimate ? `~${formatEstimateBytes(estimate.estimatedOutputBytes)}` : "calculando..."}</strong>
                    </div>
                  </div>

                  {storageCheck ? (
                    <div className={`preflight-storage-banner ${storageCheck.has_capacity ? "ok" : "danger"}`}>
                      {storageCheck.has_capacity ? <ShieldCheck size={18} /> : <TriangleAlert size={18} />}
                      <span>
                        {storageCheck.has_capacity
                          ? `Espaço em disco garantido: ${formatEstimateBytes(storageCheck.safe_available_bytes)} disponíveis na pasta de saída.`
                          : `Atenção: Espaço em disco insuficiente (${formatEstimateBytes(storageCheck.required_bytes)} necessários).`}
                      </span>
                    </div>
                  ) : null}

                  {needs4kConfirmation ? (
                    <label className="batch-risk-confirmation">
                      <input
                        type="checkbox"
                        checked={fourKConfirmed}
                        onChange={(event) => setFourKConfirmed(event.target.checked)}
                      />
                      <span>Confirmar render de lote 4K extenso ({totalJobs} jobs)</span>
                    </label>
                  ) : null}

                  <div className="preflight-hero-action">
                    <Button
                      variant="primary"
                      className="hero-launch-btn"
                      icon={<PlaySquare size={20} />}
                      label={`🚀 Criar Fila e Iniciar Render (${totalJobs} vídeos)`}
                      disabled={!canCreateBatch}
                      onClick={async () => {
                        await onCreateBatch(Math.ceil(estimate?.estimatedOutputBytes ?? 0));
                        await onProcessNext();
                      }}
                    />
                    <small>Fila persistente e resiliente no SQLite com proteção contra quedas e áudio sem estalos.</small>
                  </div>
                </div>

                <div className="wizard-footer-nav">
                  <Button
                    variant="ghost"
                    icon={<ArrowLeft size={16} />}
                    label="Voltar para Configurações"
                    onClick={() => setWizardStep(2)}
                  />
                </div>
              </div>
            )}
          </div>
        ) : (
          <>
            <label>
              Nome do lote
              <input value={batchName} onChange={(event) => onBatchNameChange(event.target.value)} />
            </label>
            <label>
              Pasta de exportacao do lote
              <div className="path-input-row">
                <input
                  value={outputDir}
                  onChange={(event) => onOutputDirChange(event.target.value)}
                  placeholder="data/renders ou outra saida permitida"
                />
                {window.videoOS?.isDesktop ? (
                  <Button
                    variant="ghost"
                    className="icon-button"
                    onClick={pickOutputDir}
                    title="Escolher pasta"
                    icon={<FolderOpen size={16} />}
                  />
                ) : null}
              </div>
            </label>
            <label>
              Variacoes por asset
              <input
                min={1}
                max={50}
                type="number"
                value={normalizedVariations}
                onChange={(event) => onVariationsChange(Math.min(50, Math.max(1, Number(event.target.value) || 1)))}
              />
            </label>
            <div className="batch-plan-grid" aria-label="Resumo do novo lote">
              <div>
                <Boxes size={17} />
                <span>Assets</span>
                <strong>{selectedAssetIds.length}</strong>
              </div>
              <div>
                <Layers3 size={17} />
                <span>Variacoes</span>
                <strong>{normalizedVariations}</strong>
              </div>
              <div>
                <PlaySquare size={17} />
                <span>Jobs</span>
                <strong>{totalJobs}</strong>
              </div>
            </div>
            {estimate ? (
              <div className={estimate.profile.id === "4k" ? "batch-estimate warning" : "batch-estimate"} aria-live="polite">
                <div className="batch-estimate-heading">
                  <div>
                    <span>Estimativa local</span>
                    <strong>{estimate.profile.label} - fila sequencial</strong>
                  </div>
                  <small>
                    {estimate.calibrationSource === "local_history"
                      ? `Historico local: ${estimate.calibrationSampleCount} jobs`
                      : "Base: benchmark completo da Passada 22"}
                  </small>
                </div>
                <div className="batch-estimate-grid">
                  <div>
                    <Clock3 size={17} />
                    <span>Tempo total</span>
                    <strong>~{formatEstimateDuration(estimate.estimatedWallSeconds)}</strong>
                  </div>
                  <div>
                    <HardDrive size={17} />
                    <span>Saida total</span>
                    <strong>~{formatEstimateBytes(estimate.estimatedOutputBytes)}</strong>
                  </div>
                  <div>
                    <MemoryStick size={17} />
                    <span>Pico por job</span>
                    <strong>~{formatEstimateBytes(estimate.peakMemoryBytes)}</strong>
                    <small>
                      {estimate.memoryCalibrationSource === "local_history"
                        ? `${estimate.memoryCalibrationSampleCount} amostra(s) + piso seguro`
                        : "benchmark conservador"}
                    </small>
                  </div>
                </div>
                {storageChecking ? (
                  <div className="batch-storage-status checking" aria-live="polite">
                    <HardDrive size={17} />
                    <span><strong>Verificando espaco</strong>Medindo a capacidade segura da pasta de exportacao.</span>
                  </div>
                ) : storageCheck ? (
                  <div className={storageCheck.has_capacity ? "batch-storage-status ok" : "batch-storage-status danger"} aria-live="polite">
                    {storageCheck.has_capacity ? <HardDrive size={17} /> : <TriangleAlert size={17} />}
                    <span>
                      <strong>{storageCheck.has_capacity ? "Espaco seguro confirmado" : "Espaco seguro insuficiente"}</strong>
                      {formatEstimateBytes(storageCheck.required_bytes)} necessarios com margem; {formatEstimateBytes(storageCheck.safe_available_bytes)} disponiveis apos reserva.
                    </span>
                  </div>
                ) : storageCheckError ? (
                  <div className="batch-storage-status warning" aria-live="polite">
                    <TriangleAlert size={17} />
                    <span><strong>Capacidade ainda nao confirmada</strong>{storageCheckError}</span>
                  </div>
                ) : null}
                {estimate.unknownDurationCount > 0 ? (
                  <p className="batch-estimate-note">
                    {estimate.unknownDurationCount} asset(s) sem duracao usam 30s na estimativa.
                  </p>
                ) : null}
                {needs4kConfirmation ? (
                  <label className="batch-risk-confirmation">
                    <input
                      type="checkbox"
                      checked={fourKConfirmed}
                      onChange={(event) => setFourKConfirmed(event.target.checked)}
                    />
                    <span>
                      <strong>Confirmar lote 4K extenso</strong>
                      {totalJobs} jobs, ~{formatEstimateDuration(estimate.renderedDurationSeconds)} de video renderizado.
                    </span>
                  </label>
                ) : null}
              </div>
            ) : null}
          </>
        )}
      </div>

      <div className="panel queue-panel">
        <div className="panel-heading">
          <div>
            <h2>Fila de render</h2>
            <p>Persistente no SQLite; o worker pode continuar depois.</p>
          </div>
          <div className="queue-heading-actions">
            <span className="queue-count">{activeJobs} ativos</span>
            {attentionJobs > 0 ? <span className="queue-count danger">{attentionJobs} requerem atencao</span> : null}
            <Button compact icon={<PlaySquare size={16} />} label="Processar 1" onClick={onProcessNext} />
          </div>
        </div>
        <div className="queue-toolbar">
          <SegmentedControl
            label="Filtrar fila"
            value={jobFilter}
            onChange={setJobFilter}
            options={[
              { value: "active", label: `Ativos ${activeJobs}` },
              { value: "attention", label: `Atencao ${attentionJobs}` },
              { value: "all", label: `Todos ${jobs.length}` }
            ]}
          />
          <span>
            {Math.min(visibleJobs.length, filteredJobs.length)} de {filteredJobs.length}
          </span>
        </div>
        <div className="job-table">
          {visibleJobs.map((job) => (
            <div className="job-row" key={job.id}>
              <div>
                <strong>{job.asset_filename ?? job.asset_id}</strong>
                <span>
                  {job.template_name} - v{job.variation_index}
                </span>
              </div>
              <StatusPill status={job.status} />
              <div className="progress-cell">
                <div className="progress-track">
                  <span style={{ width: `${job.progress}%` }} />
                </div>
                <small>{job.current_step}</small>
              </div>
              <div className="row-actions">
                {job.status === "failed" || job.status === "canceled" ? (
                  <Button
                    variant="ghost"
                    className="icon-button"
                    onClick={() => runAction(`retry-job:${job.id}`, () => onRetry(job.id))}
                    tooltip="Recolocar job na fila"
                    loading={pendingAction === `retry-job:${job.id}`}
                    icon={<RotateCcw size={16} />}
                  />
                ) : null}
                {job.status === "queued" || job.status === "processing" || job.status === "failed" ? (
                  <Button
                    variant="danger"
                    className="icon-button danger"
                    onClick={() => runAction(`cancel-job:${job.id}`, () => onCancel(job.id))}
                    tooltip={job.cancel_requested ? "Cancelamento solicitado" : "Cancelar job"}
                    disabled={job.cancel_requested}
                    loading={pendingAction === `cancel-job:${job.id}`}
                    icon={<Ban size={16} />}
                  />
                ) : null}
              </div>
            </div>
          ))}
          {filteredJobs.length === 0 ? (
            <div className="empty-state">
              {jobFilter === "active"
                ? "Nenhum job ativo. Consulte Todos para ver o historico."
                : jobFilter === "attention"
                  ? "Nenhum job falho ou cancelado."
                  : "Crie um lote para alimentar a fila."}
            </div>
          ) : null}
          {visibleJobs.length < filteredJobs.length ? (
            <Button
              variant="ghost"
              className="queue-show-more"
              icon={<ChevronDown size={16} />}
              label={`Mostrar mais ${Math.min(50, filteredJobs.length - visibleJobs.length)}`}
              onClick={() => setVisibleJobCount((current) => current + 50)}
            />
          ) : null}
        </div>
      </div>

      <div className="panel batch-history">
        <div className="panel-heading">
          <div>
            <h2>Historico de lotes</h2>
            <p>{batches.length} lote(s) persistido(s), com controles e contagens consolidadas.</p>
          </div>
        </div>
        <div className="batch-history-list">
          {batches.map((batch) => (
            <div className="history-row" key={batch.id}>
              <div className="history-main">
                <strong>{batch.name}</strong>
                <span>{batch.output_dir ? `Saida: ${batch.output_dir}` : "Saida padrao de renders"}</span>
              </div>
              <div className="history-counters" aria-label={`Resumo do lote ${batch.name}`}>
                <span className="success"><CheckCircle2 size={14} /> {batch.completed_jobs} concluidos</span>
                <span className={batch.failed_jobs > 0 ? "danger" : ""}><TriangleAlert size={14} /> {batch.failed_jobs} falhos</span>
                <span><XCircle size={14} /> {batch.canceled_jobs} cancelados</span>
                <span><PlaySquare size={14} /> {batch.active_jobs} ativos</span>
                {batchQcSummaries[batch.id] ? (
                  <span className={batchQcSummaries[batch.id].pass_rate === 100 ? "success" : "warning"}>
                    <ShieldCheck size={14} /> QC {batchQcSummaries[batch.id].pass_rate}% ({batchQcSummaries[batch.id].passed_count}/{batchQcSummaries[batch.id].total_renders})
                  </span>
                ) : null}
              </div>
              <StatusPill status={batch.status} />
              <div className="batch-history-actions">
                {batch.output_dir ? (
                  <Button
                    variant="ghost"
                    className="icon-button"
                    onClick={() => {
                      if (batch.output_dir) api.openPath(batch.output_dir);
                    }}
                    tooltip="Abrir pasta de exportacao no Explorer"
                    icon={<FolderOpen size={16} />}
                  />
                ) : null}
                {batch.completed_jobs > 0 ? (
                  <Button
                    variant="ghost"
                    className="icon-button"
                    onClick={() => handleRunBatchQc(batch.id)}
                    tooltip="Executar Quality Check do lote"
                    loading={pendingAction === `qc-batch:${batch.id}`}
                    icon={<ShieldCheck size={16} />}
                  />
                ) : null}
                {batch.is_paused && (batch.status === "paused" || batch.status === "pausing") ? (
                  <Button
                    variant="ghost"
                    className="icon-button"
                    onClick={() => runAction(`resume:${batch.id}`, () => onResumeBatch(batch.id))}
                    tooltip="Retomar lote"
                    loading={pendingAction === `resume:${batch.id}`}
                    icon={<Play size={16} />}
                  />
                ) : (batch.status === "queued" || batch.status === "processing") && batch.active_jobs > 0 ? (
                  <Button
                    variant="ghost"
                    className="icon-button"
                    onClick={() => runAction(`pause:${batch.id}`, () => onPauseBatch(batch.id))}
                    tooltip="Pausar lote"
                    loading={pendingAction === `pause:${batch.id}`}
                    icon={<Pause size={16} />}
                  />
                ) : null}
                {batch.retryable_jobs > 0 ? (
                  <Button
                    variant="ghost"
                    className="icon-button"
                    onClick={() => runAction(`retry-batch:${batch.id}`, () => onRetryBatch(batch.id))}
                    tooltip={`Recolocar ${batch.retryable_jobs} job(s) na fila`}
                    disabled={batch.status === "canceling"}
                    loading={pendingAction === `retry-batch:${batch.id}`}
                    icon={<RotateCcw size={16} />}
                  />
                ) : null}
                {batch.active_jobs > 0 || batch.failed_jobs > 0 ? (
                  <Button
                    variant="danger"
                    className="icon-button danger"
                    onClick={() => runAction(`cancel-batch:${batch.id}`, () => onCancelBatch(batch.id))}
                    tooltip="Cancelar lote inteiro"
                    disabled={batch.status === "canceling"}
                    loading={pendingAction === `cancel-batch:${batch.id}`}
                    icon={<Ban size={16} />}
                  />
                ) : null}
              </div>
            </div>
          ))}
          {batches.length === 0 ? <div className="empty-state">Nenhum lote criado.</div> : null}
        </div>
      </div>
    </section>
  );
}
