import { AlertTriangle } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { api } from "./api";
import { AgentStudio } from "./components/AgentStudio";
import { AiClipsDesk } from "./components/AiClipsDesk";
import { AppShell, type ViewKey } from "./components/AppShell";
import { AssetLibrary } from "./components/AssetLibrary";
import { BatchQueue } from "./components/BatchQueue";
import { BrandKitStudio } from "./components/BrandKitStudio";
import { BrollDesk } from "./components/BrollDesk";
import { CalendarDesk } from "./components/CalendarDesk";
import { CaptureDesk } from "./components/CaptureDesk";
import { CommandPalette } from "./components/CommandPalette";
import { EditorToolsDesk } from "./components/EditorToolsDesk";
import { HomeDesk } from "./components/HomeDesk";
import { MetricStrip } from "./components/MetricStrip";
import { MusicLab } from "./components/MusicLab";
import { PresetLibraryDesk } from "./components/PresetLibraryDesk";
import { PublishingDesk } from "./components/PublishingDesk";
import { ReviewDesk } from "./components/ReviewDesk";
import { SystemPanel } from "./components/SystemPanel";
import { TemplateStudio } from "./components/TemplateStudio";
import { TranscriptionDesk } from "./components/TranscriptionDesk";
import type { Asset, Batch, BrandKit, PlatformPreset, PublishTask, RenderJob, RenderedVideo, RenderRecipe, SystemHealth, Template, AuditEvent } from "./types";

export default function App() {
  const [activeView, setActiveView] = useState<ViewKey>("home");
  const [assets, setAssets] = useState<Asset[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [brandKits, setBrandKits] = useState<BrandKit[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [jobs, setJobs] = useState<RenderJob[]>([]);
  const [renders, setRenders] = useState<RenderedVideo[]>([]);
  const [presets, setPresets] = useState<PlatformPreset[]>([]);
  const [publishTasks, setPublishTasks] = useState<PublishTask[]>([]);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [selectedAssetIds, setSelectedAssetIds] = useState<string[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [importPath, setImportPath] = useState("");
  const [batchOutputDir, setBatchOutputDir] = useState("");
  const [batchName, setBatchName] = useState(`Lote ${new Date().toLocaleDateString("pt-BR")}`);
  const [variations, setVariations] = useState(1);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const consecutiveHealthFailures = useRef(0);

  const isApiOnline = Boolean(health);

  const handleBackupDatabase = async () => {
    try {
      const result = await api.backup();
      setMessage(`Backup criado: ${result.database}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao criar backup.");
    }
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const refresh = useCallback(async () => {
    const [healthResult, assetResult, templateResult, batchResult, jobResult, renderResult, presetResult, taskResult, auditResult, brandKitResult] =
      await Promise.allSettled([
        api.health(),
        api.assets(),
        api.templates(),
        api.batches(),
        api.jobs(),
        api.renders(),
        api.presets(),
        api.publishTasks(),
        api.audit(),
        api.brandKits()
      ]);

    if (healthResult.status === "fulfilled") {
      consecutiveHealthFailures.current = 0;
      setHealth(healthResult.value);
      setImportPath((current) => current || healthResult.value.import_roots[0] || "");
      setError(null);
    } else {
      consecutiveHealthFailures.current += 1;
      if (consecutiveHealthFailures.current >= 2) {
        setHealth(null);
        setError(healthResult.reason instanceof Error ? healthResult.reason.message : "Falha ao conectar com a API.");
      }
    }
    if (assetResult.status === "fulfilled") setAssets(assetResult.value);
    if (templateResult.status === "fulfilled") {
      setTemplates(templateResult.value);
      setSelectedTemplateId((current) => current || templateResult.value[0]?.id || "");
    }
    if (brandKitResult.status === "fulfilled") setBrandKits(brandKitResult.value);
    if (batchResult.status === "fulfilled") setBatches(batchResult.value);
    if (jobResult.status === "fulfilled") setJobs(jobResult.value);
    if (renderResult.status === "fulfilled") setRenders(renderResult.value);
    if (presetResult.status === "fulfilled") setPresets(presetResult.value);
    if (taskResult.status === "fulfilled") setPublishTasks(taskResult.value);
    if (auditResult.status === "fulfilled") setAuditEvents(auditResult.value);
    try {
      const settings = await api.settings();
      setBatchOutputDir((current) => current || settings.renders_dir || "");
    } catch {
      // Health failure already reports API state.
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = window.setInterval(() => {
      if (!document.hidden) {
        refresh();
      }
    }, 4000);

    const handleVisibilityChange = () => {
      if (!document.hidden) {
        refresh();
      }
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [refresh]);

  const selectedTemplate = useMemo(
    () => templates.find((template) => template.id === selectedTemplateId),
    [templates, selectedTemplateId]
  );

  const handleDeleteAssets = async (assetIds: string[]) => {
    if (assetIds.length === 0) return;
    const confirmed = window.confirm(
      assetIds.length === 1
        ? "Remover este video da biblioteca? O arquivo continua no disco."
        : `Remover ${assetIds.length} videos da biblioteca? Os arquivos continuam no disco.`
    );
    if (!confirmed) return;
    try {
      const result = await api.deleteAssets(assetIds);
      setSelectedAssetIds((current) => current.filter((id) => !result.deleted.some((item) => item.id === id)));
      const parts = [`${result.deleted_count} removido(s)`];
      if (result.skipped_count) parts.push(`${result.skipped_count} em uso (mantido[s])`);
      setMessage(parts.join(" · "));
      if (result.skipped.length) {
        setError(`Nao removidos (em uso em lotes/renders): ${result.skipped.map((item) => item.filename).join(", ")}`);
      }
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao remover video(s).");
    }
  };

  const handleImport = async () => {
    try {
      const result = await api.importAssets([importPath]);
      setMessage(`${result.count} video(s) importado(s).`);
      await refresh();
      setActiveView("biblioteca");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao importar.");
    }
  };

  const handleImportPaths = async (paths: string[]) => {
    try {
      const result = await api.importAssets(paths);
      setMessage(`${result.count} video(s) importado(s) pelo explorador desktop.`);
      await refresh();
      setActiveView("biblioteca");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao importar caminhos selecionados.");
    }
  };

  const handleUpload = async (files: FileList | File[]) => {
    try {
      const result = await api.uploadAssets(files);
      setMessage(`${result.count} video(s) carregado(s) pelo explorador.`);
      await refresh();
      setActiveView("biblioteca");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar pelo explorador.");
    }
  };

  const handleCreateTemplate = async (payload: Parameters<typeof api.createTemplate>[0]) => {
    try {
      const template = await api.createTemplate(payload);
      setSelectedTemplateId(template.id);
      setMessage("Template salvo.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao salvar template.");
    }
  };

  const handleUpdateTemplate = async (
    id: string,
    payload: { name: string; description: string; recipe: RenderRecipe }
  ) => {
    try {
      await api.updateTemplate(id, payload);
      setMessage("Template atualizado.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao atualizar template.");
    }
  };

  const handleDeleteTemplate = async (id: string) => {
    try {
      await api.deleteTemplate(id);
      setSelectedTemplateId("");
      setMessage("Template excluído com sucesso.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao excluir template.");
    }
  };

  const handleCreateBatch = async (estimatedOutputBytes: number) => {
    if (!selectedTemplateId || selectedAssetIds.length === 0) {
      setError("Selecione assets e template antes de criar o lote.");
      return;
    }
    try {
      await api.createBatch({
        name: batchName,
        template_id: selectedTemplateId,
        asset_ids: selectedAssetIds,
        variations,
        output_dir: batchOutputDir || undefined,
        estimated_output_bytes: estimatedOutputBytes
      });
      setMessage("Lote criado e enviado para a fila.");
      setActiveView("lotes");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao criar lote.");
    }
  };

  const handleProcessNext = async () => {
    try {
      const result = await api.processNext();
      setMessage(result.processed ? `Job ${result.processed.id.slice(0, 8)} processado.` : "Fila vazia.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao processar job.");
    }
  };

  const handleReview = async (id: string, status: RenderedVideo["status"]) => {
    try {
      await api.reviewRender(id, status);
      setMessage(status === "approved" ? "Render aprovado." : "Render reprovado.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao revisar render.");
    }
  };

  const handleCreatePackage = async (payload: Parameters<typeof api.createPublishPackage>[0]) => {
    try {
      if (payload.rendered_video_ids.length === 0 || payload.platforms.length === 0) {
        setError("Selecione renders aprovados e plataformas.");
        return;
      }
      const result = await api.createPublishPackage(payload);
      setMessage(`${result.count} pacote(s) criado(s).`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao gerar pacote.");
    }
  };

  const runQueueAction = async (action: () => Promise<unknown>, successMessage: string) => {
    setError(null);
    try {
      await action();
      setMessage(successMessage);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao atualizar a fila.");
    }
  };

  const handleCancelBatch = async (batchId: string) => {
    const batch = batches.find((item) => item.id === batchId);
    const confirmed = window.confirm(
      `Cancelar o lote "${batch?.name ?? batchId}"? Jobs pendentes serao fechados e o render ativo sera interrompido.`
    );
    if (!confirmed) return;
    await runQueueAction(() => api.cancelBatch(batchId), "Cancelamento do lote solicitado.");
  };

  const view = (() => {
    switch (activeView) {
      case "home":
        return (
          <HomeDesk
            assets={assets}
            jobs={jobs}
            renders={renders}
            publishTasks={publishTasks}
            health={health}
            onNavigate={setActiveView}
            onImport={handleImport}
            onProcessNext={handleProcessNext}
          />
        );
      case "biblioteca":
        return (
          <AssetLibrary
            assets={assets}
            selectedAssetIds={selectedAssetIds}
            importPath={importPath}
            onImportPathChange={setImportPath}
            onImport={handleImport}
            onImportPaths={handleImportPaths}
            onUpload={handleUpload}
            onToggleAsset={(assetId) =>
              setSelectedAssetIds((current) =>
                current.includes(assetId) ? current.filter((id) => id !== assetId) : [...current, assetId]
              )
            }
            onSelectAssets={setSelectedAssetIds}
            onDeleteAssets={handleDeleteAssets}
            onEditSelected={() => setActiveView("lotes")}
            onRefresh={refresh}
            onOpenClips={(assetId) => {
              setSelectedAssetIds([assetId]);
              setActiveView("clips");
            }}
          />
        );
      case "clips":
        return (
          <AiClipsDesk
            assets={assets}
            templates={templates}
            selectedAssetIds={selectedAssetIds}
            selectedTemplateId={selectedTemplateId}
            onNavigate={setActiveView}
          />
        );
      case "broll":
        return <BrollDesk />;
      case "ferramentas":
        return <EditorToolsDesk assets={assets} selectedAssetIds={selectedAssetIds} onDeleteAssets={handleDeleteAssets} />;
      case "presets":
        return <PresetLibraryDesk />;
      case "marca":
        return <BrandKitStudio />;
      case "templates":
        return (
          <TemplateStudio
            templates={templates}
            selectedTemplateId={selectedTemplateId}
            brandKits={brandKits}
            onSelectTemplate={setSelectedTemplateId}
            onCreateTemplate={handleCreateTemplate}
            onUpdateTemplate={handleUpdateTemplate}
            onDeleteTemplate={handleDeleteTemplate}
            onUseInBatch={(templateId) => {
              setSelectedTemplateId(templateId);
              setActiveView("lotes");
            }}
          />
        );
      case "lotes":
        return (
          <BatchQueue
            assets={assets}
            batches={batches}
            jobs={jobs}
            renderPerformance={health?.render_performance}
            templates={templates}
            selectedAssetIds={selectedAssetIds}
            selectedTemplateId={selectedTemplateId}
            onSelectAssets={setSelectedAssetIds}
            onSelectTemplate={setSelectedTemplateId}
            variations={variations}
            batchName={batchName}
            outputDir={batchOutputDir}
            onBatchNameChange={setBatchName}
            onOutputDirChange={setBatchOutputDir}
            onVariationsChange={setVariations}
            onCreateBatch={handleCreateBatch}
            onProcessNext={handleProcessNext}
            onRetry={(jobId) => runQueueAction(() => api.retryJob(jobId), "Job recolocado na fila.")}
            onCancel={(jobId) => runQueueAction(() => api.cancelJob(jobId), "Cancelamento do job solicitado.")}
            onPauseBatch={(batchId) => runQueueAction(() => api.pauseBatch(batchId), "Lote pausado.")}
            onResumeBatch={(batchId) => runQueueAction(() => api.resumeBatch(batchId), "Lote retomado.")}
            onCancelBatch={handleCancelBatch}
            onRetryBatch={(batchId) =>
              runQueueAction(() => api.retryBatch(batchId), "Jobs falhos e cancelados recolocados na fila.")
            }
          />
        );
      case "revisao":
        return <ReviewDesk renders={renders} onReview={handleReview} />;
      case "publicacao":
        return (
          <PublishingDesk
            renders={renders}
            presets={presets}
            tasks={publishTasks}
            onCreatePackage={handleCreatePackage}
            onUpdateTask={async (id, status) => {
              await api.updatePublishTask(id, status);
              await refresh();
            }}
          />
        );
      case "agentes":
        return <AgentStudio onNavigate={setActiveView} />;
      case "captura":
        return <CaptureDesk />;
      case "transcricao":
        return <TranscriptionDesk assets={assets} onDeleteAssets={handleDeleteAssets} />;
      case "musica":
        return <MusicLab />;
      case "calendario":
        return <CalendarDesk tasks={publishTasks} onNavigate={setActiveView} />;
      case "sistema":
        return (
          <SystemPanel
            health={health}
            auditEvents={auditEvents}
            lastMessage={message}
            onBackup={async () => {
              const result = await api.backup();
              setMessage(`Backup criado: ${result.database}`);
              await refresh();
            }}
          />
        );
      default:
        return null;
    }
  })();

  return (
    <>
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onNavigate={setActiveView}
        onRefresh={refresh}
        onBackup={handleBackupDatabase}
      />
      <AppShell
        activeView={activeView}
        onViewChange={setActiveView}
        onImport={handleImport}
        onNewBatch={() => setActiveView("lotes")}
        onProcessNext={handleProcessNext}
        onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
        isApiOnline={isApiOnline}
        jobs={jobs}
      >
        {activeView === "home" ? (
          <MetricStrip assets={assets} jobs={jobs} renders={renders} publishTasks={publishTasks} />
        ) : null}
        {error ? (
          <div className="toast error-toast" role="alert" aria-live="assertive">
            <AlertTriangle size={18} aria-hidden="true" />
            <span>{error}</span>
            <button onClick={() => setError(null)} type="button" aria-label="Fechar mensagem de erro">
              Fechar
            </button>
          </div>
        ) : null}
        {message ? (
          <div className="toast" role="status" aria-live="polite">
            <span>{message}</span>
            <button onClick={() => setMessage(null)} type="button" aria-label="Fechar notificação">
              Fechar
            </button>
          </div>
        ) : null}
        {["home", "biblioteca", "templates", "lotes"].includes(activeView) ? (
          <div className="context-line">
            <span>Template ativo</span>
            <strong>{selectedTemplate?.name ?? "nenhum"}</strong>
          </div>
        ) : null}
        {view}
      </AppShell>
    </>
  );
}
