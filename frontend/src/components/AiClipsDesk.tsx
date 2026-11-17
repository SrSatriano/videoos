import {
  AlertCircle,
  BarChart3,
  Check,
  CheckCircle2,
  Clapperboard,
  Copy,
  Flame,
  Layers,
  Rocket,
  Scissors,
  Sparkles,
  Video,
  Zap
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { api } from "../api";
import type { Asset, MinedClip, Template } from "../types";
import type { ViewKey } from "./AppShell";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

interface AiClipsDeskProps {
  assets: Asset[];
  templates: Template[];
  selectedAssetIds: string[];
  selectedTemplateId: string;
  onNavigate: (view: ViewKey) => void;
}

export function AiClipsDesk({
  assets,
  templates,
  selectedAssetIds,
  selectedTemplateId,
  onNavigate
}: AiClipsDeskProps) {
  const [activeAssetId, setActiveAssetId] = useState<string>(
    selectedAssetIds[0] || assets[0]?.id || ""
  );
  const [templateId, setTemplateId] = useState<string>(
    selectedTemplateId || templates[0]?.id || ""
  );

  const [minSeconds, setMinSeconds] = useState(15);
  const [maxSeconds, setMaxSeconds] = useState(60);
  const [targetCount, setTargetCount] = useState(5);
  const [minScoreFilter, setMinScoreFilter] = useState(50);

  const [enableCaptions, setEnableCaptions] = useState(true);
  const [captionStyle, setCaptionStyle] = useState("hormozi");
  const [enableMusic, setEnableMusic] = useState(false);
  const [musicVolume, setMusicVolume] = useState(0.15);
  const [enableJumpcut, setEnableJumpcut] = useState(true);

  const [clips, setClips] = useState<MinedClip[]>([]);
  const [selectedClipIndices, setSelectedClipIndices] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [creatingBatch, setCreatingBatch] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [copiedClipIndex, setCopiedClipIndex] = useState<number | null>(null);
  const [runningAutopilot, setRunningAutopilot] = useState(false);

  const activeAsset = useMemo(
    () => assets.find((a) => a.id === activeAssetId) || assets[0] || null,
    [assets, activeAssetId]
  );

  useEffect(() => {
    if (selectedAssetIds[0] && selectedAssetIds[0] !== activeAssetId) {
      setActiveAssetId(selectedAssetIds[0]);
    }
  }, [selectedAssetIds]);

  useEffect(() => {
    if (selectedTemplateId && selectedTemplateId !== templateId) {
      setTemplateId(selectedTemplateId);
    }
  }, [selectedTemplateId]);

  useEffect(() => {
    if (!activeAsset) return;
    let active = true;
    api
      .getAssetClips(activeAsset.id)
      .then((existing) => {
        if (!active) return;
        if (existing && existing.length > 0) {
          setClips(existing);
          setSelectedClipIndices(existing.map((_, idx) => idx));
          setStatusMessage(`${existing.length} cortes recuperados do acervo.`);
        }
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [activeAsset?.id]);

  const handleMine = async () => {
    if (!activeAsset) {
      setStatusMessage("Importe ou selecione um vídeo antes de minerar.");
      return;
    }
    try {
      setLoading(true);
      setStatusMessage("Analisando transcrição e minerando cortes com Viral Score...");
      const res = await api.mineViralClips(activeAsset.id, {
        min_seconds: minSeconds,
        max_seconds: maxSeconds,
        target_count: targetCount
      });
      setClips(res.clips);
      setSelectedClipIndices(res.clips.map((_, idx) => idx));
      setStatusMessage(
        `${res.clips.length} cortes virais identificados com sucesso pelo motor ${res.engine}!`
      );
    } catch (err) {
      setStatusMessage(
        `Erro na mineração: ${err instanceof Error ? err.message : "Falha ao minerar cortes."}`
      );
    } finally {
      setLoading(false);
    }
  };

  const toggleSelectClip = (index: number) => {
    setSelectedClipIndices((prev) =>
      prev.includes(index) ? prev.filter((i) => i !== index) : [...prev, index]
    );
  };

  const handleSelectAll = () => {
    setSelectedClipIndices(filteredClips.map((_, i) => i));
  };

  const handleDeselectAll = () => {
    setSelectedClipIndices([]);
  };

  const copyToClipboard = (text: string, index: number) => {
    void navigator.clipboard.writeText(text);
    setCopiedClipIndex(index);
    setTimeout(() => setCopiedClipIndex(null), 2500);
  };

  const handleCreateBatch = async (clipsToProcess: MinedClip[], batchLabel?: string) => {
    if (!activeAsset) return;
    const targetTpl = templateId || templates[0]?.id;
    if (!targetTpl) {
      setStatusMessage("Selecione um template base antes de criar o lote.");
      return;
    }
    if (clipsToProcess.length === 0) {
      setStatusMessage("Selecione ao menos um corte para enviar ao lote.");
      return;
    }
    try {
      setCreatingBatch(true);
      setStatusMessage("Criando lote de renderização 9:16...");
      const res = await api.createBatchFromClips({
        asset_id: activeAsset.id,
        template_id: targetTpl,
        clips: clipsToProcess,
        batch_name: batchLabel || `Shorts Virais - ${activeAsset.filename.slice(0, 30)}`,
        enable_captions: enableCaptions,
        caption_style: captionStyle,
        enable_music: enableMusic,
        music_volume: musicVolume,
        enable_jumpcut: enableJumpcut
      });
      setStatusMessage(`Lote criado com sucesso: ${res.name}! Redirecionando para a fila...`);
      setTimeout(() => {
        onNavigate("lotes");
      }, 700);
    } catch (err) {
      setStatusMessage(
        `Erro ao criar lote: ${err instanceof Error ? err.message : "Falha na criação."}`
      );
    } finally {
      setCreatingBatch(false);
    }
  };

  const handleRunAutopilot = async () => {
    if (!activeAsset) {
      setStatusMessage("Selecione um vídeo primeiro para o Piloto Automático.");
      return;
    }
    setRunningAutopilot(true);
    setStatusMessage("🚀 Piloto Automático em ação: minerando cortes virais, aplicando legendas, música e criando lote 9:16...");
    try {
      const res = await api.runAutopilotPipeline({
        asset_id: activeAsset.id,
        min_score: minScoreFilter,
        max_clips: targetCount,
        enable_captions: enableCaptions,
        caption_style: captionStyle,
        enable_music: enableMusic,
        music_volume: musicVolume,
        enable_jumpcut: enableJumpcut,
        batch_name: `Autopilot: ${activeAsset.filename.slice(0, 30)}`
      });
      setStatusMessage(`🎉 Piloto Automático concluiu! ${res.total_jobs} cortes produzidos no lote '${res.batch_name}'. Redirecionando...`);
      setTimeout(() => {
        onNavigate("lotes");
      }, 1000);
    } catch (err: any) {
      setStatusMessage(`Erro no Piloto Automático: ${err?.message || "Falha na execução"}`);
    } finally {
      setRunningAutopilot(false);
    }
  };

  const filteredClips = useMemo(() => {
    return clips.filter((c) => c.viral_score >= minScoreFilter);
  }, [clips, minScoreFilter]);

  const selectedClipsList = useMemo(() => {
    return selectedClipIndices
      .map((idx) => filteredClips[idx])
      .filter((c): c is MinedClip => Boolean(c));
  }, [filteredClips, selectedClipIndices]);

  return (
    <section className="view-grid two-column">
      <div className="panel" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Automação de Cortes Virais</span>
            <h2>AI Viral Miner & Shorts Station</h2>
          </div>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "4px 10px",
              borderRadius: "6px",
              background: "rgba(77, 163, 255, 0.12)",
              color: "var(--blue)",
              fontSize: "12px",
              fontWeight: 600
            }}
          >
            <Sparkles size={14} /> Estilo Opus / Vizard
          </span>
        </div>

        <p style={{ margin: 0, color: "var(--muted)", fontSize: "13.5px", lineHeight: "1.5" }}>
          Transcreva seu vídeo, identifique os momentos de maior retenção (Viral Score), destaque
          os primeiros 3 segundos de gancho (Hook) e converta em lotes verticais 9:16 prontos para
          renderizar com legendas sincronizadas.
        </p>

        <div
          style={{
            display: "grid",
            gap: "1rem",
            background: "rgba(255, 255, 255, 0.02)",
            padding: "1rem",
            borderRadius: "8px",
            border: "1px solid var(--line)"
          }}
        >
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <label className="settings-path-field">
              <span>Vídeo de Origem</span>
              <select
                value={activeAsset?.id || ""}
                onChange={(e) => setActiveAssetId(e.target.value)}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  background: "var(--surface-2)",
                  border: "1px solid var(--line)",
                  borderRadius: "6px",
                  color: "var(--text)"
                }}
              >
                {assets.map((asset) => (
                  <option key={asset.id} value={asset.id}>
                    {asset.filename} ({formatTime(asset.duration_seconds || 0)})
                  </option>
                ))}
              </select>
            </label>

            <label className="settings-path-field">
              <span>Template de Edição 9:16</span>
              <select
                value={templateId}
                onChange={(e) => setTemplateId(e.target.value)}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  background: "var(--surface-2)",
                  border: "1px solid var(--line)",
                  borderRadius: "6px",
                  color: "var(--text)"
                }}
              >
                {templates.map((tpl) => (
                  <option key={tpl.id} value={tpl.id}>
                    {tpl.name} ({tpl.recipe?.format ? `${tpl.recipe.format.width}x${tpl.recipe.format.height}` : "9:16"})
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
              gap: "0.75rem"
            }}
          >
            <label className="settings-path-field">
              <span>Duração Mín. (s)</span>
              <input
                type="number"
                min={5}
                max={60}
                value={minSeconds}
                onChange={(e) => setMinSeconds(Number(e.target.value))}
              />
            </label>

            <label className="settings-path-field">
              <span>Duração Máx. (s)</span>
              <input
                type="number"
                min={15}
                max={180}
                value={maxSeconds}
                onChange={(e) => setMaxSeconds(Number(e.target.value))}
              />
            </label>

            <label className="settings-path-field">
              <span>Meta de Cortes</span>
              <input
                type="number"
                min={1}
                max={20}
                value={targetCount}
                onChange={(e) => setTargetCount(Number(e.target.value))}
              />
            </label>

            <label className="settings-path-field">
              <span>Score Mínimo: {minScoreFilter}%</span>
              <input
                type="range"
                min={40}
                max={90}
                step={5}
                value={minScoreFilter}
                onChange={(e) => setMinScoreFilter(Number(e.target.value))}
                style={{ marginTop: "8px" }}
              />
            </label>
          </div>

          {/* Diretrizes Condicionais de Edição */}
          <div
            style={{
              display: "grid",
              gap: "0.75rem",
              background: "rgba(0, 0, 0, 0.25)",
              padding: "0.85rem",
              borderRadius: "6px",
              border: "1px dashed var(--line)"
            }}
          >
            <strong style={{ fontSize: "12.5px", color: "var(--text)" }}>
              Diretrizes Condicionais de Edição para o Lote:
            </strong>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "0.75rem" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={enableCaptions}
                    onChange={(e) => setEnableCaptions(e.target.checked)}
                  />
                  <span>Adicionar Legendas Dinâmicas</span>
                </label>
                {enableCaptions && (
                  <select
                    value={captionStyle}
                    onChange={(e) => setCaptionStyle(e.target.value)}
                    style={{
                      padding: "4px 8px",
                      background: "var(--surface-3)",
                      border: "1px solid var(--line)",
                      borderRadius: "4px",
                      fontSize: "12px",
                      color: "var(--text)",
                      marginTop: "2px"
                    }}
                  >
                    <option value="hormozi">Estilo Hormozi (Destaque Amarelo)</option>
                    <option value="neon_cyan">Cyberpunk Neon (Ciano)</option>
                    <option value="minimal_white">Minimalista Clean (Branco)</option>
                    <option value="bold_red">Impacto Forte (Vermelho)</option>
                  </select>
                )}
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={enableMusic}
                    onChange={(e) => setEnableMusic(e.target.checked)}
                  />
                  <span>Adicionar Música de Fundo</span>
                </label>
                {enableMusic && (
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "2px" }}>
                    <span style={{ fontSize: "11px", color: "var(--muted)" }}>Volume: {Math.round(musicVolume * 100)}%</span>
                    <input
                      type="range"
                      min={0.05}
                      max={0.4}
                      step={0.05}
                      value={musicVolume}
                      onChange={(e) => setMusicVolume(Number(e.target.value))}
                      style={{ flex: 1 }}
                    />
                  </div>
                )}
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={enableJumpcut}
                    onChange={(e) => setEnableJumpcut(e.target.checked)}
                  />
                  <span>Cortar Pausas & Silêncios (&gt;0.4s)</span>
                </label>
                <small style={{ fontSize: "11px", color: "var(--muted)" }}>
                  Acelera o ritmo e aumenta a retenção do espectador
                </small>
              </div>
            </div>
          </div>

          <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
            <Button
              variant="primary"
              compact
              loading={loading}
              icon={<Sparkles size={16} />}
              label={loading ? "Minerando Cortes com IA..." : "Minerar Cortes Virais (AI)"}
              onClick={handleMine}
            />
            <Button
              variant="secondary"
              compact
              loading={runningAutopilot}
              icon={<Rocket size={16} />}
              label={runningAutopilot ? "Executando Piloto Automático..." : "🚀 Piloto Automático 1-Clique"}
              onClick={handleRunAutopilot}
            />
            {statusMessage && (
              <span
                style={{
                  fontSize: "12.5px",
                  color: statusMessage.startsWith("Erro") ? "var(--red)" : "var(--green)"
                }}
              >
                {statusMessage}
              </span>
            )}
          </div>
        </div>

        {filteredClips.length > 0 && (
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "13px", color: "var(--muted)", fontWeight: 600 }}>
              Exibindo {filteredClips.length} cortes (Filtro &gt;= {minScoreFilter}%)
            </span>
            <div style={{ display: "flex", gap: "8px" }}>
              <Button variant="ghost" compact label="Selecionar Todos" onClick={handleSelectAll} />
              <Button variant="ghost" compact label="Desmarcar Todos" onClick={handleDeselectAll} />
            </div>
          </div>
        )}

        <div className="ai-clips-grid">
          {filteredClips.map((clip, index) => {
            const isSelected = selectedClipIndices.includes(index);
            const scoreClass =
              clip.viral_score >= 80 ? "high" : clip.viral_score >= 65 ? "medium" : "regular";

            const copyText = `${clip.suggested_copy}\n\n${(clip.suggested_hashtags || []).map((t) => (t.startsWith("#") ? t : `#${t}`)).join(" ")}`;

            return (
              <article key={clip.id || index} className={`clip-card ${isSelected ? "selected" : ""}`}>
                <div className="clip-card-header">
                  <div className="clip-card-title-group">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleSelectClip(index)}
                      style={{ cursor: "pointer", width: "16px", height: "16px" }}
                    />
                    <strong style={{ fontSize: "14px", color: "var(--text)" }}>
                      {clip.suggested_title || `Corte #${index + 1}`}
                    </strong>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span className={`viral-score-badge ${scoreClass}`}>
                      {clip.viral_score >= 80 ? (
                        <Flame size={14} />
                      ) : clip.viral_score >= 65 ? (
                        <Zap size={14} />
                      ) : (
                        <BarChart3 size={14} />
                      )}
                      {clip.viral_score}% Viral Score
                    </span>
                    <span
                      style={{
                        fontSize: "12px",
                        color: "var(--muted)",
                        background: "rgba(255,255,255,0.06)",
                        padding: "3px 8px",
                        borderRadius: "4px"
                      }}
                    >
                      {formatTime(clip.start_seconds)} - {formatTime(clip.end_seconds)} (
                      {clip.duration}s)
                    </span>
                  </div>
                </div>

                <div className="clip-hook-box">
                  <strong>🎯 Gancho de Retenção (0-3s): </strong>
                  <span>"{clip.hook}"</span>
                </div>

                {clip.reason && (
                  <p style={{ margin: 0, fontSize: "12.5px", color: "var(--muted)" }}>
                    💡 <strong>Análise:</strong> {clip.reason}
                  </p>
                )}

                <div className="clip-copy-box">
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center"
                    }}
                  >
                    <span style={{ fontWeight: 600, color: "var(--text)" }}>
                      Legenda & Copy Sugerida:
                    </span>
                    <button
                      type="button"
                      onClick={() => copyToClipboard(copyText, index)}
                      style={{
                        background: "none",
                        border: "none",
                        color: "var(--blue)",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "4px",
                        fontSize: "11px"
                      }}
                    >
                      {copiedClipIndex === index ? (
                        <>
                          <Check size={12} /> Copiado!
                        </>
                      ) : (
                        <>
                          <Copy size={12} /> Copiar Copy
                        </>
                      )}
                    </button>
                  </div>
                  <div>{clip.suggested_copy}</div>
                  {clip.suggested_hashtags && clip.suggested_hashtags.length > 0 && (
                    <div className="clip-hashtags">
                      {clip.suggested_hashtags.map((tag, tIdx) => (
                        <span key={tIdx} className="clip-hashtag-tag">
                          {tag.startsWith("#") ? tag : `#${tag}`}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginTop: "4px"
                  }}
                >
                  <span style={{ fontSize: "11.5px", color: "var(--muted)" }}>
                    Categoria: <strong>{clip.category || "Destaque"}</strong>
                  </span>
                  <Button
                    variant="ghost"
                    compact
                    icon={<Scissors size={14} />}
                    label="Gerar Lote deste Corte"
                    onClick={() => handleCreateBatch([clip], `Short: ${clip.suggested_title || "Corte"}`)}
                  />
                </div>
              </article>
            );
          })}

          {filteredClips.length === 0 && !loading && (
            <div className="empty-state" style={{ padding: "2.5rem 1rem", textAlign: "center" }}>
              <Video size={36} style={{ color: "var(--muted)", margin: "0 auto 0.75rem" }} />
              <strong>Nenhum corte minerado ainda.</strong>
              <p style={{ margin: "0.5rem 0 0", color: "var(--muted)", fontSize: "13px" }}>
                Clique no botão "Minerar Cortes Virais (AI)" acima para que a inteligência
                artificial transcreva o vídeo, calcule os Viral Scores e descubra os ganchos mais
                fortes.
              </p>
            </div>
          )}
        </div>

        {selectedClipsList.length > 0 && (
          <div
            style={{
              position: "sticky",
              bottom: "1rem",
              background: "rgba(17, 21, 26, 0.95)",
              border: "1px solid var(--blue)",
              boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
              borderRadius: "8px",
              padding: "12px 18px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              backdropFilter: "blur(8px)",
              zIndex: 10
            }}
          >
            <div>
              <strong style={{ color: "var(--text)", fontSize: "14px" }}>
                {selectedClipsList.length} corte(s) selecionado(s)
              </strong>
              <div style={{ fontSize: "12px", color: "var(--muted)" }}>
                Exportação em 9:16 com o template selecionado
              </div>
            </div>
            <Button
              variant="primary"
              compact
              loading={creatingBatch}
              icon={<Layers size={16} />}
              label={`Criar Lote 9:16 (${selectedClipsList.length})`}
              onClick={() => handleCreateBatch(selectedClipsList)}
            />
          </div>
        )}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
        <Card title="Receita de Viralização" eyebrow="Shorts & Reels">
          <div className="rule-list">
            <span>Hook nos Primeiros 3s</span>
            <span>Corte Seco e Dinâmico</span>
            <span>Legendas Centrais 9:16</span>
            <span>CTA no Encerramento</span>
          </div>
          <div className="preview-phone">
            <div className="safe-band top">HOOK EM DESTAQUE</div>
            <Clapperboard size={42} />
            <div className="safe-band bottom">LEGENDA SINCRONIZADA</div>
          </div>
        </Card>

        <Card title="Estatísticas do Algoritmo" eyebrow="Métricas">
          <div style={{ display: "grid", gap: "10px", fontSize: "13px" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--muted)" }}>Motor de Análise:</span>
              <strong>Google Gemini 2.0 / Heurístico</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--muted)" }}>Detecção de Hooks:</span>
              <strong style={{ color: "var(--green)" }}>Ativa (0-3s)</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--muted)" }}>Síntese Neural:</span>
              <strong>Edge-TTS + Timestamps SRT</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--muted)" }}>Formato Padrão:</span>
              <strong>9:16 Vertical (1080x1920)</strong>
            </div>
          </div>
        </Card>
      </div>
    </section>
  );
}
