import { ClipboardCheck, Download, FileJson2, FolderOpen, LoaderCircle, PackageCheck, ShieldAlert, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { StatusPill } from "./StatusPill";
import { api } from "../api";
import type { PackageQualityReport, PlatformPreset, PublishTask, RenderedVideo } from "../types";

interface PublishingDeskProps {
  renders: RenderedVideo[];
  presets: PlatformPreset[];
  tasks: PublishTask[];
  onCreatePackage: (payload: {
    rendered_video_ids: string[];
    platforms: PlatformPreset["platform"][];
    caption: string;
    hashtags: string[];
    output_dir?: string;
  }) => void;
  onUpdateTask: (id: string, status: PublishTask["status"]) => void;
}

function formatBytes(value: number | null | undefined) {
  if (!value || value <= 0) return "Nao medido";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  return `${(value / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function reportLoudness(report: PackageQualityReport) {
  const loudness = report.actual?.loudness;
  if (loudness?.status === "measured" && loudness.integrated_lufs != null) {
    return `${loudness.integrated_lufs.toFixed(1)} LUFS`;
  }
  if (loudness?.status === "silent") return "Silencio";
  if (loudness?.status === "no_audio") return "Sem audio";
  return "Nao medido";
}

export function PublishingDesk({ renders, presets, tasks, onCreatePackage, onUpdateTask }: PublishingDeskProps) {
  const approved = useMemo(() => renders.filter((render) => render.status === "approved"), [renders]);
  const [selectedRenderIds, setSelectedRenderIds] = useState<string[]>([]);
  const [platforms, setPlatforms] = useState<PlatformPreset["platform"][]>(["instagram_reels"]);
  const [caption, setCaption] = useState("Comenta \"eu quero\" que eu te mostro como funciona.");
  const [hashtags, setHashtags] = useState("#automacao #instagram #conteudodark #reels");
  const [outputDir, setOutputDir] = useState("");
  const [openReportId, setOpenReportId] = useState<string | null>(null);
  const [reportByTask, setReportByTask] = useState<Record<string, PackageQualityReport>>({});
  const [loadingReportId, setLoadingReportId] = useState<string | null>(null);
  const [reportError, setReportError] = useState<{ taskId: string; message: string } | null>(null);
  const canCreatePackage = selectedRenderIds.length > 0 && platforms.length > 0;

  useEffect(() => {
    const approvedIds = new Set(approved.map((render) => render.id));
    setSelectedRenderIds((current) => current.filter((id) => approvedIds.has(id)));
  }, [approved]);

  const togglePlatform = (platform: PlatformPreset["platform"]) => {
    setPlatforms((current) =>
      current.includes(platform) ? current.filter((item) => item !== platform) : [...current, platform]
    );
  };

  const toggleRender = (renderId: string) => {
    setSelectedRenderIds((current) =>
      current.includes(renderId) ? current.filter((item) => item !== renderId) : [...current, renderId]
    );
  };

  const submit = () => {
    if (!canCreatePackage) return;
    onCreatePackage({
      rendered_video_ids: selectedRenderIds,
      platforms,
      caption,
      output_dir: outputDir || undefined,
      hashtags: hashtags
        .split(/\s+/)
        .map((tag) => tag.trim())
        .filter(Boolean)
    });
  };

  const chooseOutputFolder = async () => {
    const path = await window.videoOS?.pickFolder();
    if (path) setOutputDir(path);
  };

  const toggleReport = async (taskId: string) => {
    if (openReportId === taskId) {
      setOpenReportId(null);
      return;
    }
    setOpenReportId(taskId);
    setReportError(null);
    if (reportByTask[taskId]) return;
    setLoadingReportId(taskId);
    try {
      const report = await api.publishQualityReport(taskId);
      setReportByTask((current) => ({ ...current, [taskId]: report }));
    } catch (err) {
      setReportError({
        taskId,
        message: err instanceof Error ? err.message : "Falha ao carregar o relatorio."
      });
    } finally {
      setLoadingReportId(null);
    }
  };

  const platformLabel = (platform: string) =>
    presets.find((preset) => preset.platform === platform)?.label ?? platform.replace(/_/g, " ");

  return (
    <section className="view-grid publish-layout">
      <div className="panel">
        <div className="panel-heading">
          <div>
            <h2>Pacote de publicacao</h2>
            <p>Gera arquivos para postagem manual e checklist por plataforma.</p>
          </div>
          <button
            className="primary-button compact"
            disabled={!canCreatePackage}
            onClick={submit}
            title={!selectedRenderIds.length ? "Selecione ao menos um render aprovado." : !platforms.length ? "Selecione ao menos uma plataforma." : undefined}
            type="button"
          >
            <PackageCheck size={16} />
            Gerar pacote
          </button>
        </div>

        <div className="approved-list">
          {approved.map((render) => (
            <button
              className={selectedRenderIds.includes(render.id) ? "approved-row selected" : "approved-row"}
              key={render.id}
              onClick={() => toggleRender(render.id)}
              type="button"
            >
              <span>{render.id.slice(0, 8)}</span>
              <strong>{render.duration_seconds ? `${render.duration_seconds.toFixed(1)}s` : "render aprovado"}</strong>
            </button>
          ))}
          {approved.length === 0 ? (
            <div className="empty-state compact-empty">
              Nenhum render aprovado. Conclua a revisao antes de gerar pacotes.
            </div>
          ) : null}
        </div>

        <div className="platform-grid">
          {presets.map((preset) => (
            <button
              className={platforms.includes(preset.platform) ? "platform-button selected" : "platform-button"}
              key={preset.platform}
              onClick={() => togglePlatform(preset.platform)}
              type="button"
            >
              <ClipboardCheck size={17} />
              <span>{preset.label}</span>
            </button>
          ))}
        </div>

        <label>
          Legenda
          <textarea value={caption} onChange={(event) => setCaption(event.target.value)} />
        </label>
        <label>
          Hashtags
          <input value={hashtags} onChange={(event) => setHashtags(event.target.value)} />
        </label>
        <label>
          Pasta de saida dos pacotes
          <input
            value={outputDir}
            onChange={(event) => setOutputDir(event.target.value)}
            placeholder="Opcional: C:\\Users\\seu usuario\\Videos\\Pacotes"
          />
        </label>
        {window.videoOS?.isDesktop ? (
          <button className="secondary-button compact" onClick={chooseOutputFolder} type="button">
            <FolderOpen size={16} />
            Explorar saida
          </button>
        ) : null}
      </div>

      <div className="panel task-panel">
        <h2>Tarefas geradas</h2>
        <div className="task-list">
          {tasks.map((task) => {
            const report = reportByTask[task.id];
            const isOpen = openReportId === task.id;
            return (
              <article className={isOpen ? "task-entry report-open" : "task-entry"} key={task.id}>
                <div className="task-row">
                  <div className="task-main">
                    <strong>{platformLabel(task.platform)}</strong>
                    <span title={task.package_dir}>{task.package_dir}</span>
                  </div>
                  <StatusPill status={task.status} />
                  <div className="task-controls">
                    <button
                      aria-label={`Visualizar relatorio de ${platformLabel(task.platform)}`}
                      className={isOpen ? "icon-button active" : "icon-button"}
                      onClick={() => toggleReport(task.id)}
                      title="Visualizar relatorio"
                      type="button"
                    >
                      {loadingReportId === task.id ? <LoaderCircle className="animate-spin" size={17} /> : <FileJson2 size={17} />}
                    </button>
                    <a
                      aria-label={`Baixar relatorio de ${platformLabel(task.platform)}`}
                      className="icon-button"
                      download
                      href={api.publishQualityReportUrl(task.id)}
                      title="Baixar relatorio JSON"
                    >
                      <Download size={17} />
                    </a>
                    <select
                      aria-label={`Status de ${platformLabel(task.platform)}`}
                      value={task.status}
                      onChange={(event) => onUpdateTask(task.id, event.target.value as PublishTask["status"])}
                    >
                      <option value="ready">Pronto</option>
                      <option value="posted">Publicado</option>
                      <option value="failed">Falhou</option>
                      <option value="archived">Arquivado</option>
                    </select>
                  </div>
                </div>
                {isOpen ? (
                  <div className="quality-report-viewer">
                    {reportError?.taskId === task.id ? <div className="inline-error">{reportError.message}</div> : null}
                    {report ? (
                      <>
                        <div className="quality-report-heading">
                          <div>
                            {report.passed ? <ShieldCheck size={18} /> : <ShieldAlert size={18} />}
                            <strong>{report.passed ? "Relatorio aprovado" : "Relatorio com pendencias"}</strong>
                          </div>
                          <span>{report.schema_version}</span>
                        </div>
                        <div className="quality-report-metrics">
                          <div><span>Score</span><strong>{report.score}/100</strong></div>
                          <div><span>Resolucao</span><strong>{report.actual?.width && report.actual?.height ? `${report.actual.width}x${report.actual.height}` : "Nao medida"}</strong></div>
                          <div><span>Arquivo</span><strong>{formatBytes(report.actual?.file_size_bytes)}</strong></div>
                          <div><span>Loudness</span><strong>{reportLoudness(report)}</strong></div>
                        </div>
                        {report.audio_issues?.length ? (
                          <div className="report-audio-issues">
                            {report.audio_issues.map((item) => (
                              <span className={`quality-issue ${item.severity}`} key={item.code ?? item.message}>{item.message}</span>
                            ))}
                          </div>
                        ) : null}
                        <div className="quality-report-checks">
                          {report.checks.map((check) => (
                            <div className={check.passed ? "passed" : "failed"} key={check.id}>
                              {check.passed ? <ShieldCheck size={14} /> : <ShieldAlert size={14} />}
                              <span>{check.label}</span>
                              <strong>{check.passed ? "OK" : "Revisar"}</strong>
                            </div>
                          ))}
                        </div>
                      </>
                    ) : loadingReportId === task.id ? <div className="report-loading">Carregando relatorio...</div> : null}
                  </div>
                ) : null}
              </article>
            );
          })}
          {tasks.length === 0 ? (
            <div className="empty-state">
              <FolderOpen size={24} />
              Pacotes finais vao aparecer aqui.
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
