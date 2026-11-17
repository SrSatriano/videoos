import { Check, Crosshair, Download, Eye, EyeOff, Filter, PackageCheck, ShieldCheck, Smartphone, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { StatusPill } from "./StatusPill";
import { api } from "../api";
import type { PlatformPreset, QualityCheckResult, RenderedVideo, SafeZoneGuide, IntegrityCheckResult } from "../types";

interface ReviewDeskProps {
  renders: RenderedVideo[];
  onReview: (id: string, status: RenderedVideo["status"]) => void;
}

type SafeZoneMode = PlatformPreset["platform"] | "universal";

const SAFE_ZONE_GUIDES: Record<SafeZoneMode, SafeZoneGuide> = {
  universal: {
    platform: "universal",
    label: "Universal",
    top_pct: 14,
    right_pct: 18,
    bottom_pct: 24,
    left_pct: 6,
    notes: ["Zona combinada para Reels, TikTok e Shorts."]
  },
  instagram_reels: {
    platform: "instagram_reels",
    label: "Instagram",
    top_pct: 14,
    right_pct: 10,
    bottom_pct: 22,
    left_pct: 6,
    notes: ["Reels com area central protegida para mensagem, legenda e CTA."]
  },
  tiktok: {
    platform: "tiktok",
    label: "TikTok",
    top_pct: 12,
    right_pct: 18,
    bottom_pct: 24,
    left_pct: 6,
    notes: ["Folga maior na direita e no rodape por causa dos controles."]
  },
  youtube_shorts: {
    platform: "youtube_shorts",
    label: "Shorts",
    top_pct: 10,
    right_pct: 12,
    bottom_pct: 20,
    left_pct: 6,
    notes: ["Area central para titulo visual, legenda e elementos de marca."]
  }
};

const SAFE_ZONE_OPTIONS: SafeZoneMode[] = ["universal", "instagram_reels", "tiktok", "youtube_shorts"];

function guideStyle(guide: SafeZoneGuide) {
  return {
    top: `${guide.top_pct}%`,
    right: `${guide.right_pct}%`,
    bottom: `${guide.bottom_pct}%`,
    left: `${guide.left_pct}%`
  };
}

function formatBytes(value: number | null | undefined) {
  if (!value || value <= 0) return "Nao medido";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  return `${(value / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatSeconds(value: number | null | undefined) {
  return value && value > 0 ? `${value.toFixed(1)}s` : "Nao medido";
}

function readinessCopy(result: QualityCheckResult) {
  const technicalPassed = result.reports.every((report) => report.passed);
  if (result.package_ready) {
    return {
      title: "Pronto para pacote",
      detail: "QC tecnico aprovado e revisao editorial concluida."
    };
  }
  if (!technicalPassed) {
    return {
      title: "Ajustes tecnicos necessarios",
      detail: "Corrija os bloqueios indicados antes de gerar o pacote."
    };
  }
  if (result.review_status === "rejected") {
    return {
      title: "Bloqueado pela revisao",
      detail: "O arquivo passou no QC tecnico, mas esta reprovado editorialmente."
    };
  }
  return {
    title: "Aguardando aprovacao",
    detail: "O arquivo passou no QC tecnico e ainda precisa de aprovacao editorial."
  };
}

function loudnessValue(result: QualityCheckResult) {
  const loudness = result.metadata.loudness;
  if (loudness?.status === "measured" && loudness.integrated_lufs != null) {
    return `${loudness.integrated_lufs.toFixed(1)} LUFS`;
  }
  if (loudness?.status === "no_audio") return "Sem audio";
  return "Nao medida";
}

function bitrateValue(value: number | null | undefined) {
  return value != null && value > 0 ? `${Math.round(value)} kbps` : "Nao medido";
}

function truePeakValue(result: QualityCheckResult) {
  const value = result.metadata.loudness?.true_peak_dbtp;
  return value != null ? `${value.toFixed(1)} dBTP` : "Nao medido";
}

export function ReviewDesk({ renders, onReview }: ReviewDeskProps) {
  const [qualityResults, setQualityResults] = useState<Record<string, QualityCheckResult>>({});
  const [checkingId, setCheckingId] = useState<string | null>(null);
  const [qualityError, setQualityError] = useState<string | null>(null);
  const [safeZoneMode, setSafeZoneMode] = useState<SafeZoneMode>("universal");
  const [showSafeZone, setShowSafeZone] = useState(true);
  const [integrityResults, setIntegrityResults] = useState<Record<string, IntegrityCheckResult & { loading?: boolean }>>({});
  const [checkingAllIntegrity, setCheckingAllIntegrity] = useState(false);
  const [statusFilter, setStatusFilter] = useState<"all" | "pending_review" | "approved" | "rejected">("all");
  const [packaging, setPackaging] = useState(false);
  const [packageFeedback, setPackageFeedback] = useState<string | null>(null);

  const filteredRenders = useMemo(() => {
    if (statusFilter === "all") return renders;
    return renders.filter((r) => r.status === statusFilter);
  }, [renders, statusFilter]);

  const pendingCount = renders.filter((r) => r.status === "pending_review").length;
  const approvedCount = renders.filter((r) => r.status === "approved").length;
  const rejectedCount = renders.filter((r) => r.status === "rejected").length;

  const handleCreatePackageFromApproved = async () => {
    const approvedIds = renders.filter((r) => r.status === "approved").map((r) => r.id);
    if (!approvedIds.length) return;
    setPackaging(true);
    try {
      const res = await api.createPublishPackage({
        rendered_video_ids: approvedIds,
        platforms: ["instagram_reels", "tiktok", "youtube_shorts"],
        caption: "Vídeo aprovado e pronto para publicação.",
        hashtags: ["#videoos", "#reels", "#shorts", "#viral"]
      });
      setPackageFeedback(`Pacote com ${res.count} publicação(ões) criado com sucesso! Acesse a aba "Publicação" para agendar.`);
      setTimeout(() => setPackageFeedback(null), 5000);
    } catch (err: any) {
      alert(err.message || "Falha ao criar pacote de publicação.");
    } finally {
      setPackaging(false);
    }
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select" || (e.target as HTMLElement)?.isContentEditable) {
        return;
      }
      if (e.key === "z" || e.key === "Z") {
        e.preventDefault();
        setShowSafeZone((prev) => !prev);
      } else if (e.key === "s" || e.key === "S") {
        e.preventDefault();
        setSafeZoneMode((current) => {
          const idx = SAFE_ZONE_OPTIONS.indexOf(current);
          const nextIdx = (idx + 1) % SAFE_ZONE_OPTIONS.length;
          return SAFE_ZONE_OPTIONS[nextIdx];
        });
      } else if (e.key === "a" || e.key === "A") {
        const target = renders.find((r) => r.status === "pending_review") ?? renders[0];
        if (target) {
          e.preventDefault();
          updateReview(target.id, "approved");
        }
      } else if (e.key === "r" || e.key === "R") {
        const target = renders.find((r) => r.status === "pending_review") ?? renders[0];
        if (target) {
          e.preventDefault();
          updateReview(target.id, "rejected");
        }
      } else if (e.code === "Space") {
        const videos = Array.from(document.querySelectorAll<HTMLVideoElement>(".render-media video"));
        if (videos.length > 0) {
          e.preventDefault();
          const first = videos[0];
          if (first.paused) {
            first.play().catch(() => {});
          } else {
            first.pause();
          }
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [renders]);

  const runIntegrityCheck = async (renderId: string) => {
    setIntegrityResults((current) => ({
      ...current,
      [renderId]: { loading: true, valid: false, error_type: null, message: "Avaliando integridade..." }
    }));
    try {
      const result = await api.checkRenderIntegrity(renderId);
      setIntegrityResults((current) => ({ ...current, [renderId]: result }));
    } catch (err: any) {
      setIntegrityResults((current) => ({
        ...current,
        [renderId]: {
          valid: false,
          error_type: "check_timeout_or_failed",
          message: err.message || "Erro desconhecido ao validar integridade."
        }
      }));
    }
  };

  const activeGuide = SAFE_ZONE_GUIDES[safeZoneMode];
  const safeWidth = 100 - activeGuide.left_pct - activeGuide.right_pct;
  const safeHeight = 100 - activeGuide.top_pct - activeGuide.bottom_pct;

  const runQualityCheck = async (renderId: string) => {
    setCheckingId(renderId);
    setQualityError(null);
    try {
      const result = await api.qualityCheckRender(renderId);
      setQualityResults((current) => ({ ...current, [renderId]: result }));
    } catch (err) {
      setQualityError(err instanceof Error ? err.message : "Falha ao validar render.");
    } finally {
      setCheckingId(null);
    }
  };

  const updateReview = (renderId: string, status: RenderedVideo["status"]) => {
    setQualityResults((current) => {
      const next = { ...current };
      delete next[renderId];
      return next;
    });
    onReview(renderId, status);
  };

  const runAllIntegrityChecks = async () => {
    setCheckingAllIntegrity(true);
    try {
      const pending = renders.filter((render) => !integrityResults[render.id]?.valid);
      for (let index = 0; index < pending.length; index += 3) {
        await Promise.all(pending.slice(index, index + 3).map((render) => runIntegrityCheck(render.id)));
      }
    } finally {
      setCheckingAllIntegrity(false);
    }
  };

  return (
    <section className="review-grid">
      <div className="panel review-studio-bar">
        <div className="review-studio-title">
          <Crosshair size={18} />
          <div>
            <h2>Safe Zone Studio</h2>
            <span>
              {activeGuide.label}: {safeWidth}% largura util, {safeHeight}% altura util
            </span>
          </div>
        </div>
        <div className="review-studio-actions">
          <button
            className="secondary-button compact"
            disabled={checkingAllIntegrity || renders.length === 0}
            onClick={runAllIntegrityChecks}
            type="button"
          >
            <ShieldCheck size={16} />
            {checkingAllIntegrity ? "Verificando..." : "Verificar todos"}
          </button>
          <button
            className="secondary-button compact"
            onClick={() => setShowSafeZone((prev) => !prev)}
            title="Alternar visibilidade da Safe Zone (Atalho: Z)"
            type="button"
          >
            {showSafeZone ? <EyeOff size={15} /> : <Eye size={15} />}
            {showSafeZone ? "Ocultar Guia [Z]" : "Exibir Guia [Z]"}
          </button>
          <div className="safe-zone-tabs" aria-label="Plataforma da area segura">
            {SAFE_ZONE_OPTIONS.map((option) => (
              <button
                className={safeZoneMode === option ? "safe-zone-tab active" : "safe-zone-tab"}
                key={option}
                onClick={() => setSafeZoneMode(option)}
                type="button"
              >
                {option === "universal" ? <Crosshair size={15} /> : <Smartphone size={15} />}
                {SAFE_ZONE_GUIDES[option].label}
              </button>
            ))}
          </div>
        </div>
      </div>
      {packageFeedback ? (
        <div style={{ padding: "8px 12px", background: "rgba(99, 226, 143, 0.15)", border: "1px solid #63e28f", borderRadius: "6px", color: "#63e28f", fontSize: "0.85rem" }}>
          {packageFeedback}
        </div>
      ) : null}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px", padding: "8px 4px" }}>
        <div className="review-filter-group">
          <span style={{ fontSize: "0.8rem", color: "var(--muted)", display: "flex", alignItems: "center", gap: "4px" }}>
            <Filter size={14} /> Filtro:
          </span>
          {(
            [
              { id: "all", label: `Todos (${renders.length})` },
              { id: "pending_review", label: `Pendentes (${pendingCount})` },
              { id: "approved", label: `Aprovados (${approvedCount})` },
              { id: "rejected", label: `Reprovados (${rejectedCount})` }
            ] as const
          ).map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={`review-filter-btn ${statusFilter === tab.id ? "active" : ""}`}
              onClick={() => setStatusFilter(tab.id)}
              aria-pressed={statusFilter === tab.id}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          {approvedCount > 0 ? (
            <button
              className="primary-button compact"
              disabled={packaging}
              onClick={handleCreatePackageFromApproved}
              type="button"
              style={{ display: "flex", alignItems: "center", gap: "6px" }}
            >
              <PackageCheck size={16} />
              {packaging ? "Gerando..." : `Gerar Pacote de Publicação (${approvedCount})`}
            </button>
          ) : null}
          <span style={{ fontSize: "0.75rem", color: "var(--muted)" }}>
            Exibindo {filteredRenders.length} de {renders.length}
          </span>
        </div>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "4px 8px", fontSize: "0.8rem", color: "var(--muted-2)" }}>
        <span>Atalhos de teclado: <code>[A]</code> Aprovar · <code>[R]</code> Reprovar · <code>[S]</code> Plataforma · <code>[Z]</code> Máscara · <code>[Espaço]</code> Play/Pause</span>
      </div>
      {qualityError ? <div className="inline-error review-error">{qualityError}</div> : null}
      {filteredRenders.map((render) => (
        <article className="panel render-card" key={render.id}>
          <div className="render-media">
            {render.media_url ? (
              <video src={render.media_url} poster={render.thumbnail_url ?? undefined} controls playsInline />
            ) : (
              <div className="empty-state">Midia indisponivel</div>
            )}
            {showSafeZone ? (
              <div className="safe-zone-overlay" aria-hidden="true">
                <span className="safe-zone-block safe-zone-top" style={{ height: `${activeGuide.top_pct}%` }} />
                <span className="safe-zone-block safe-zone-right" style={{ width: `${activeGuide.right_pct}%` }} />
                <span className="safe-zone-block safe-zone-bottom" style={{ height: `${activeGuide.bottom_pct}%` }} />
                <span className="safe-zone-block safe-zone-left" style={{ width: `${activeGuide.left_pct}%` }} />
                <span className="safe-zone-frame" style={guideStyle(activeGuide)}>
                  <strong>AREA SEGURA</strong>
                  <small>{activeGuide.label}</small>
                </span>
                <span className="safe-zone-center horizontal" />
                <span className="safe-zone-center vertical" />
              </div>
            ) : null}
          </div>
          {showSafeZone ? (
            <div className="safe-zone-metrics">
              <span>Topo {activeGuide.top_pct}%</span>
              <span>Direita {activeGuide.right_pct}%</span>
              <span>Rodape {activeGuide.bottom_pct}%</span>
              <span>Esquerda {activeGuide.left_pct}%</span>
            </div>
          ) : null}
          <div className="render-telemetry" aria-label="Telemetria do render">
            <div>
              <span>Arquivo</span>
              <strong>{formatBytes(render.size_bytes)}</strong>
            </div>
            <div>
              <span>Render</span>
              <strong>{formatSeconds(render.render_seconds)}</strong>
            </div>
            <div>
              <span>Pico RAM</span>
              <strong>{formatBytes(render.peak_rss_bytes)}</strong>
            </div>
          </div>
          <div className="render-info">
            <div>
              <strong>{render.width && render.height ? `${render.width}x${render.height}` : "Render"}</strong>
              <span>{render.duration_seconds ? `${render.duration_seconds.toFixed(1)}s` : "Duracao pendente"}</span>
            </div>
            <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
              {(() => {
                const integrity = integrityResults[render.id];
                if (!integrity) {
                  return (
                    <button className="integrity-tag pending" onClick={() => runIntegrityCheck(render.id)} type="button">
                      Verificar integridade
                    </button>
                  );
                }
                if (integrity.loading) {
                  return <span className="integrity-tag loading">Legibilidade: checando...</span>;
                }
                return (
                  <button
                    className={`integrity-tag ${integrity.valid ? "valid" : "corrupt"}`}
                    title={`${integrity.message}${integrity.fix ? ' | Correção: ' + integrity.fix : ''}`}
                    onClick={() => runIntegrityCheck(render.id)}
                    type="button"
                  >
                    {integrity.valid ? "✓ Decodificável" : `⚠ ${integrity.error_type === "file_missing" ? "Arquivo Ausente" : "Corrompido"}`}
                  </button>
                );
              })()}
              <StatusPill status={render.status} />
            </div>
          </div>
          <div className="render-actions">
            <button className="secondary-button compact" onClick={() => updateReview(render.id, "rejected")} type="button">
              <X size={16} />
              Reprovar
            </button>
            <button className="secondary-button compact" disabled={checkingId === render.id} onClick={() => runQualityCheck(render.id)} type="button">
              <ShieldCheck size={16} />
              {checkingId === render.id ? "QC..." : "QC"}
            </button>
            {render.media_url ? (
              <a className="secondary-button compact" href={render.media_url} download>
                <Download size={16} />
                Baixar
              </a>
            ) : null}
            <button className="primary-button compact" onClick={() => updateReview(render.id, "approved")} type="button">
              <Check size={16} />
              Aprovar
            </button>
          </div>
          {qualityResults[render.id] ? (
            <div className="quality-panel">
              <div className={qualityResults[render.id].package_ready ? "quality-readiness ready" : "quality-readiness blocked"}>
                <ShieldCheck size={18} />
                <div>
                  <strong>{readinessCopy(qualityResults[render.id]).title}</strong>
                  <span>{readinessCopy(qualityResults[render.id]).detail}</span>
                  <small className={`qc-cache-state ${qualityResults[render.id].analysis_cache.status}`}>
                    {qualityResults[render.id].analysis_cache.status === "hit" ? "Analise reutilizada" : "Analise atualizada"}
                  </small>
                </div>
              </div>
              <div className="media-analysis-grid">
                <div>
                  <span>Video</span>
                  <strong>{qualityResults[render.id].metadata.video_codec?.toUpperCase() ?? "Nao detectado"}</strong>
                </div>
                <div>
                  <span>Audio</span>
                  <strong>{qualityResults[render.id].metadata.audio_codec?.toUpperCase() ?? (qualityResults[render.id].metadata.has_audio === false ? "Sem audio" : "Nao detectado")}</strong>
                </div>
                <div>
                  <span>FPS</span>
                  <strong>{qualityResults[render.id].metadata.fps?.toFixed(2) ?? "Nao medido"}</strong>
                </div>
                <div>
                  <span>Bitrate</span>
                  <strong>{bitrateValue(qualityResults[render.id].metadata.bitrate_kbps)}</strong>
                </div>
                <div>
                  <span>Loudness</span>
                  <strong>{loudnessValue(qualityResults[render.id])}</strong>
                </div>
                <div>
                  <span>True peak</span>
                  <strong>{truePeakValue(qualityResults[render.id])}</strong>
                </div>
              </div>
              {qualityResults[render.id].audio_issues.length ? (
                <div className="audio-quality-alerts" aria-label="Alertas de audio">
                  {qualityResults[render.id].audio_issues.map((audioIssue) => (
                    <span className={`quality-issue ${audioIssue.severity}`} key={audioIssue.code ?? audioIssue.message}>
                      {audioIssue.message}
                    </span>
                  ))}
                </div>
              ) : null}
              {qualityResults[render.id].reports.map((report) => (
                <div className={report.passed ? "quality-row passed" : "quality-row failed"} key={report.platform}>
                  <strong>{report.label}</strong>
                  <span>{report.score}/100</span>
                  <small>{report.issues.find((issue) => issue.severity !== "info")?.message ?? "Sem bloqueios tecnicos."}</small>
                  <div className="quality-issue-list">
                    {report.issues.filter((issue) => !issue.code?.startsWith("audio_")).slice(0, 3).map((issue) => (
                      <span className={`quality-issue ${issue.severity}`} key={`${report.platform}-${issue.severity}-${issue.message}`}>
                        {issue.message}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </article>
      ))}
      {renders.length === 0 ? (
        <div className="panel empty-review">
          <h2>Revisao</h2>
          <p>Quando o worker concluir renders, eles aparecem aqui com player e botoes de aprovacao.</p>
        </div>
      ) : null}
    </section>
  );
}
