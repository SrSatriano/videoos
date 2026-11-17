import {
  Captions,
  Copy,
  Eye,
  EyeOff,
  Frame,
  Music2,
  Palette,
  PlaySquare,
  Plus,
  RotateCcw,
  Save,
  Search,
  ShieldCheck,
  Sparkles,
  Trash2,
  Type
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import type { BrandKit, RenderRecipe, Template } from "../types";
import { Button } from "./ui/Button";

const resolutionPresets = [
  { id: "1080p", label: "1080p (Reels/TikTok/Shorts)", width: 1080, height: 1920, crf: 23 },
  { id: "2k", label: "2K Vertical", width: 1440, height: 2560, crf: 21 },
  { id: "4k", label: "4K Vertical UHD", width: 2160, height: 3840, crf: 19 }
];

const defaultFrame: NonNullable<RenderRecipe["frame"]> = {
  enabled: false,
  background_color: "#ffffff",
  header_background_color: "#ffffff",
  divider_color: "#e02424",
  divider_height: 8,
  header_height: 340,
  video_margin: 0,
  video_fit: "crop",
  logo_path: "",
  logo_size: 164,
  channel_name: "",
  channel_color: "#111111",
  channel_font_size: 72
};

const defaultCaptions: NonNullable<RenderRecipe["captions"]> = {
  enabled: false,
  burned_srt_path: "",
  style: "hormozi"
};

const baseRecipe: RenderRecipe = {
  format: { width: 1080, height: 1920, fit: "crop", fps: 30 },
  trim: { start: 0, end: null },
  text: {
    top: "",
    bottom: "",
    font_size: 74,
    font_color: "white",
    border_color: "black",
    border_width: 6
  },
  captions: defaultCaptions,
  frame: defaultFrame,
  broll: [],
  watermark: { enabled: true, text: "@sistema.dark", position: "bottom_right" },
  audio: { preserve: true, normalize: true, music_path: "", music_volume: 0.22, original_volume: 1 },
  export: { codec: "libx264", crf: 23, preset: "veryfast" }
};

function withRecipeDefaults(recipe: RenderRecipe | undefined): RenderRecipe {
  const source = recipe ?? baseRecipe;
  return {
    ...baseRecipe,
    ...source,
    format: { ...baseRecipe.format, ...source.format },
    trim: { ...baseRecipe.trim, ...source.trim },
    text: { ...baseRecipe.text, ...source.text },
    captions: { ...defaultCaptions, ...(source.captions ?? {}) },
    frame: { ...defaultFrame, ...(source.frame ?? {}) },
    broll: source.broll ?? [],
    watermark: { ...baseRecipe.watermark, ...source.watermark },
    audio: { ...baseRecipe.audio, ...source.audio },
    export: { ...baseRecipe.export, ...source.export }
  };
}

function selectedResolutionId(recipe: RenderRecipe): string {
  const preset = resolutionPresets.find(
    (item) => item.width === recipe.format.width && item.height === recipe.format.height
  );
  return preset?.id ?? "custom";
}

const SAFE_ZONES = {
  universal: { top: "14%", bottom: "24%", right: "18%", left: "6%", label: "Universal (Reels + TikTok + Shorts)" },
  reels: { top: "14%", bottom: "22%", right: "12%", left: "6%", label: "Instagram Reels" },
  tiktok: { top: "12%", bottom: "24%", right: "18%", left: "6%", label: "TikTok" },
  shorts: { top: "10%", bottom: "20%", right: "14%", left: "6%", label: "YouTube Shorts" }
};

interface TemplateStudioProps {
  templates: Template[];
  selectedTemplateId: string;
  brandKits?: BrandKit[];
  onSelectTemplate: (id: string) => void;
  onCreateTemplate: (payload: { name: string; description: string; recipe: RenderRecipe }) => void;
  onUpdateTemplate?: (id: string, payload: { name: string; description: string; recipe: RenderRecipe }) => void;
  onDeleteTemplate?: (id: string) => void;
  onUseInBatch?: (templateId: string) => void;
}

export function TemplateStudio({
  templates,
  selectedTemplateId,
  brandKits = [],
  onSelectTemplate,
  onCreateTemplate,
  onUpdateTemplate,
  onDeleteTemplate,
  onUseInBatch
}: TemplateStudioProps) {
  const selected = templates.find((template) => template.id === selectedTemplateId);
  const [name, setName] = useState("Template canal - moldura em massa");
  const [recipe, setRecipe] = useState<RenderRecipe>(() => withRecipeDefaults(selected?.recipe));
  const [templateQuery, setTemplateQuery] = useState("");
  const [selectedBrandKitId, setSelectedBrandKitId] = useState<string>("");
  const [showSafeZones, setShowSafeZones] = useState(true);
  const [safeZonePlatform, setSafeZonePlatform] = useState<keyof typeof SAFE_ZONES>("universal");
  const [feedback, setFeedback] = useState<string | null>(null);

  const frameRecipe = recipe.frame ?? defaultFrame;
  const captionRecipe: NonNullable<RenderRecipe["captions"]> = recipe.captions ?? defaultCaptions;
  const activeResolution = useMemo(() => selectedResolutionId(recipe), [recipe]);

  const visibleTemplates = useMemo(() => {
    const query = templateQuery.trim().toLocaleLowerCase("pt-BR");
    if (!query) return templates;
    return templates.filter((template) =>
      `${template.name} ${template.description ?? ""}`.toLocaleLowerCase("pt-BR").includes(query)
    );
  }, [templateQuery, templates]);

  useEffect(() => {
    if (selected) {
      setRecipe(withRecipeDefaults(selected.recipe));
      setName(selected.name);
    }
  }, [selected?.id]);

  const setResolution = (id: string) => {
    const preset = resolutionPresets.find((item) => item.id === id);
    if (!preset) return;
    const scale = preset.height / 1920;
    setRecipe({
      ...recipe,
      format: { ...recipe.format, width: preset.width, height: preset.height },
      text: {
        ...recipe.text,
        font_size: Math.round(74 * scale),
        border_width: Math.max(2, Math.round(6 * scale))
      },
      frame: {
        ...frameRecipe,
        header_height: Math.round(340 * scale),
        divider_height: Math.max(6, Math.round(8 * scale)),
        logo_size: Math.round((164 * scale) / 2) * 2,
        channel_font_size: Math.round(72 * scale)
      },
      export: { ...recipe.export, crf: preset.crf }
    });
  };

  const handleApplyBrandKit = () => {
    const kit = brandKits.find((b) => b.id === selectedBrandKitId);
    if (!kit) return;
    const cfg = kit.config;

    const updatedFrame: NonNullable<RenderRecipe["frame"]> = {
      ...frameRecipe,
      divider_color: (cfg.divider_color as string) || (cfg.primary_color as string) || frameRecipe.divider_color,
      header_background_color: (cfg.background_color as string) || frameRecipe.header_background_color,
      background_color: (cfg.background_color as string) || frameRecipe.background_color,
      channel_color: (cfg.text_color as string) || (cfg.primary_color as string) || frameRecipe.channel_color,
      logo_path: (cfg.logo_url as string) || frameRecipe.logo_path,
      channel_name: frameRecipe.channel_name || kit.name
    };

    const updatedWatermark = {
      ...recipe.watermark,
      text: (cfg.watermark_text as string) || recipe.watermark.text
    };

    const updatedCaptions = {
      ...captionRecipe,
      style: (cfg.karaoke_preset as string) || captionRecipe.style || "hormozi"
    };

    setRecipe({
      ...recipe,
      frame: updatedFrame,
      watermark: updatedWatermark,
      captions: updatedCaptions
    });

    setFeedback(`Identidade do Brand Kit "${kit.name}" aplicada ao template com sucesso!`);
    setTimeout(() => setFeedback(null), 4000);
  };

  const handleSaveUpdate = () => {
    if (!selected) {
      handleSaveNew();
      return;
    }
    if (onUpdateTemplate) {
      onUpdateTemplate(selected.id, {
        name,
        description: selected.description || "Receita de producao em massa atualizada.",
        recipe
      });
      setFeedback("Template atualizado com sucesso!");
      setTimeout(() => setFeedback(null), 3000);
    } else {
      onCreateTemplate({
        name,
        description: "Receita de producao em massa atualizada.",
        recipe
      });
    }
  };

  const handleSaveNew = () => {
    onCreateTemplate({
      name: name.includes("Cópia") || name.includes("copia") ? name : `${name} (Novo)`,
      description: "Nova receita de producao em massa com moldura, captions, musica e export.",
      recipe
    });
    setFeedback("Novo template criado!");
    setTimeout(() => setFeedback(null), 3000);
  };

  const handleDelete = () => {
    if (!selected || !onDeleteTemplate) return;
    if (window.confirm(`Tem certeza que deseja excluir o template "${selected.name}"?`)) {
      onDeleteTemplate(selected.id);
    }
  };

  return (
    <section className="view-grid template-workbench">
      <div className="panel template-library-panel">
        <div className="panel-heading">
          <div>
            <h2>Templates</h2>
            <p>Receitas reutilizaveis estilo Canva para aplicacao em lote.</p>
          </div>
          <Button
            compact
            variant="ghost"
            icon={<Plus size={16} />}
            label="Novo"
            onClick={() => {
              onSelectTemplate("");
              setName("Novo Template de Producao");
              setRecipe(baseRecipe);
            }}
          />
        </div>
        <div className="template-library-toolbar">
          <label className="template-search-field">
            <Search size={16} />
            <input
              aria-label="Buscar templates"
              placeholder="Buscar por nome ou descricao"
              value={templateQuery}
              onChange={(event) => setTemplateQuery(event.target.value)}
            />
          </label>
          <span className="template-result-count">
            {visibleTemplates.length}/{templates.length}
          </span>
        </div>
        <div className="template-list">
          {visibleTemplates.map((template) => (
            <button
              className={template.id === selectedTemplateId ? "template-row selected" : "template-row"}
              key={template.id}
              onClick={() => onSelectTemplate(template.id)}
              type="button"
            >
              <Type size={18} />
              <span>
                <strong>{template.name}</strong>
                <small>{template.description || "Sem descricao"}</small>
              </span>
            </button>
          ))}
          {visibleTemplates.length === 0 ? <div className="empty-state">Nenhum template encontrado.</div> : null}
        </div>
      </div>

      <div className="panel template-editor mass-template-editor">
        <div className="panel-heading">
          <div>
            <h2>Estúdio de Template</h2>
            <p>Composição de camadas, moldura, Safe Zones, legendas karaokê e áudio.</p>
          </div>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            {selected && onUseInBatch ? (
              <Button
                variant="ghost"
                compact
                icon={<PlaySquare size={16} />}
                label="Usar no Lote"
                onClick={() => onUseInBatch(selected.id)}
              />
            ) : null}
            {selected && onDeleteTemplate ? (
              <Button
                variant="danger"
                compact
                icon={<Trash2 size={16} />}
                label="Excluir"
                onClick={handleDelete}
              />
            ) : null}
            <Button
              variant="secondary"
              compact
              icon={<Copy size={16} />}
              label="Salvar Como Novo"
              onClick={handleSaveNew}
            />
            <Button
              variant="primary"
              compact
              icon={<Save size={16} />}
              label={selected ? "Salvar Alterações" : "Criar Template"}
              onClick={handleSaveUpdate}
            />
          </div>
        </div>

        {feedback ? (
          <div style={{ padding: "8px 12px", background: "rgba(99, 226, 143, 0.15)", border: "1px solid #63e28f", borderRadius: "6px", color: "#63e28f", fontSize: "0.85rem", marginBottom: "12px" }}>
            {feedback}
          </div>
        ) : null}

        {brandKits.length > 0 ? (
          <div style={{ display: "flex", alignItems: "center", gap: "12px", background: "rgba(30, 41, 59, 0.6)", padding: "10px 14px", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.08)", marginBottom: "16px" }}>
            <Palette size={18} style={{ color: "var(--blue)" }} />
            <div style={{ flex: 1 }}>
              <strong style={{ fontSize: "0.85rem", display: "block" }}>Sincronizar com Brand Kit (Identidade da Marca)</strong>
              <small style={{ color: "var(--muted)" }}>Herde cores, logo, marca d'água e estilo de legenda com 1 clique.</small>
            </div>
            <select
              value={selectedBrandKitId}
              onChange={(e) => setSelectedBrandKitId(e.target.value)}
              style={{ padding: "4px 8px", background: "#0b0f13", border: "1px solid var(--line)", borderRadius: "6px", color: "var(--text)" }}
            >
              <option value="">Selecione um Brand Kit...</option>
              {brandKits.map((kit) => (
                <option key={kit.id} value={kit.id}>{kit.name}{kit.is_default ? " (Padrão)" : ""}</option>
              ))}
            </select>
            <Button
              variant="secondary"
              compact
              disabled={!selectedBrandKitId}
              icon={<Sparkles size={14} />}
              label="Herdar Marca"
              onClick={handleApplyBrandKit}
            />
          </div>
        ) : null}

        <label>
          Nome do Template
          <input value={name} onChange={(event) => setName(event.target.value)} />
        </label>

        {/* MOLDURA E LIVE PREVIEW INTERATIVO COM SAFE ZONES */}
        <section className="template-section">
          <div className="section-title">
            <Frame size={17} />
            <strong>Layout 9:16 e Live Preview (Safe Zones)</strong>
          </div>
          <div className="frame-editor-grid" style={{ gridTemplateColumns: "220px 1fr", gap: "20px" }}>
            {/* 9:16 Canvas Mockup */}
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "0.75rem", color: "var(--muted)" }}>Preview 9:16</span>
                <button
                  type="button"
                  onClick={() => setShowSafeZones(!showSafeZones)}
                  style={{ background: "none", border: "none", color: showSafeZones ? "#63e28f" : "var(--muted)", cursor: "pointer", display: "flex", alignItems: "center", gap: "4px", fontSize: "0.75rem" }}
                >
                  {showSafeZones ? <Eye size={13} /> : <EyeOff size={13} />}
                  Safe Zones
                </button>
              </div>

              <div
                style={{
                  position: "relative",
                  width: "210px",
                  height: "373px",
                  borderRadius: "10px",
                  overflow: "hidden",
                  border: "1px solid rgba(255,255,255,0.15)",
                  background: frameRecipe.enabled ? (frameRecipe.background_color || "#ffffff") : "#0f172a",
                  boxShadow: "0 10px 25px rgba(0,0,0,0.5)",
                  display: "flex",
                  flexDirection: "column"
                }}
              >
                {/* Header Moldura */}
                {frameRecipe.enabled ? (
                  <div
                    style={{
                      height: `${Math.min(25, Math.max(12, Math.round((frameRecipe.header_height / (recipe.format.height || 1920)) * 100)))}%`,
                      background: frameRecipe.header_background_color || "#ffffff",
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      padding: "4px 8px",
                      borderBottom: `${Math.max(2, Math.round(frameRecipe.divider_height / 3))}px solid ${frameRecipe.divider_color || "#e02424"}`
                    }}
                  >
                    <div
                      style={{
                        width: "28px",
                        height: "28px",
                        borderRadius: "50%",
                        background: frameRecipe.divider_color || "#e02424",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "#ffffff",
                        fontSize: "10px",
                        fontWeight: 700,
                        flexShrink: 0
                      }}
                    >
                      {frameRecipe.channel_name ? frameRecipe.channel_name.charAt(0).toUpperCase() : "V"}
                    </div>
                    <span
                      style={{
                        color: frameRecipe.channel_color || "#111111",
                        fontSize: "0.75rem",
                        fontWeight: 700,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap"
                      }}
                    >
                      {frameRecipe.channel_name || "Canal Oficial"}
                    </span>
                  </div>
                ) : null}

                {/* Inner Video Container */}
                <div
                  style={{
                    flex: 1,
                    position: "relative",
                    background: "radial-gradient(circle, #1e293b 0%, #090d16 100%)",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    padding: "8px",
                    overflow: "hidden"
                  }}
                >
                  {/* Top Text Preview */}
                  <div style={{ textAlign: "center", minHeight: "18px" }}>
                    {recipe.text.top ? (
                      <span
                        style={{
                          color: recipe.text.font_color || "#ffffff",
                          fontSize: "0.7rem",
                          fontWeight: 800,
                          textShadow: "1px 1px 2px #000000",
                          display: "inline-block",
                          lineHeight: 1.1
                        }}
                      >
                        {recipe.text.top}
                      </span>
                    ) : null}
                  </div>

                  {/* Karaoke Caption Simulated Demo */}
                  <div style={{ textAlign: "center", padding: "4px" }}>
                    {captionRecipe.enabled ? (
                      <div
                        style={{
                          display: "inline-block",
                          padding: "3px 6px",
                          borderRadius: "4px",
                          fontSize: "0.68rem",
                          fontWeight: 800,
                          color: "#ffffff",
                          textShadow: "1px 1px 2px #000000"
                        }}
                      >
                        <span>ESSE É O </span>
                        <span
                          style={{
                            color:
                              captionRecipe.style === "neon_cyan"
                                ? "#00ffff"
                                : captionRecipe.style === "bold_red"
                                  ? "#ff2222"
                                  : captionRecipe.style === "minimal_white"
                                    ? "#f0f0f0"
                                    : "#ffff00",
                            borderBottom: "1.5px solid currentColor"
                          }}
                        >
                          SEGREDO
                        </span>
                        <span> VIRAL</span>
                      </div>
                    ) : (
                      <small style={{ color: "rgba(255,255,255,0.25)", fontSize: "0.6rem" }}>Área de Vídeo</small>
                    )}
                  </div>

                  {/* Bottom Text / CTA Preview */}
                  <div style={{ textAlign: "center", minHeight: "18px" }}>
                    {recipe.text.bottom ? (
                      <span
                        style={{
                          color: recipe.text.font_color || "#ffffff",
                          fontSize: "0.65rem",
                          fontWeight: 700,
                          textShadow: "1px 1px 2px #000000",
                          display: "inline-block",
                          lineHeight: 1.1
                        }}
                      >
                        {recipe.text.bottom}
                      </span>
                    ) : null}
                  </div>

                  {/* Watermark Preview */}
                  {recipe.watermark.enabled && recipe.watermark.text ? (
                    <span
                      style={{
                        position: "absolute",
                        bottom: "6px",
                        right: "6px",
                        fontSize: "0.55rem",
                        color: "rgba(255,255,255,0.6)",
                        fontWeight: 600,
                        textShadow: "1px 1px 1px #000000"
                      }}
                    >
                      {recipe.watermark.text}
                    </span>
                  ) : null}

                  {/* Safe Zone Overlay */}
                  {showSafeZones ? (
                    <div
                      style={{
                        position: "absolute",
                        top: SAFE_ZONES[safeZonePlatform].top,
                        bottom: SAFE_ZONES[safeZonePlatform].bottom,
                        right: SAFE_ZONES[safeZonePlatform].right,
                        left: SAFE_ZONES[safeZonePlatform].left,
                        border: "1.5px dashed rgba(239, 68, 68, 0.7)",
                        borderRadius: "4px",
                        pointerEvents: "none",
                        display: "flex",
                        alignItems: "flex-start",
                        justifyContent: "center",
                        background: "rgba(239, 68, 68, 0.05)"
                      }}
                    >
                      <span
                        style={{
                          fontSize: "0.55rem",
                          color: "#ef4444",
                          background: "rgba(0,0,0,0.7)",
                          padding: "1px 3px",
                          borderRadius: "2px",
                          fontWeight: 700
                        }}
                      >
                        Safe Zone
                      </span>
                    </div>
                  ) : null}
                </div>
              </div>

              {/* Safe Zone platform selector */}
              {showSafeZones ? (
                <div className="safezone-btn-group">
                  {(["universal", "reels", "tiktok", "shorts"] as const).map((p) => (
                    <button
                      key={p}
                      type="button"
                      className={`safezone-btn ${safeZonePlatform === p ? "active" : ""}`}
                      onClick={() => setSafeZonePlatform(p)}
                      aria-pressed={safeZonePlatform === p}
                    >
                      {p.toUpperCase()}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>

            {/* Frame & Moldura controls */}
            <div className="form-grid frame-fields">
              <div className="toggle-line section-toggle" style={{ gridColumn: "1 / -1" }}>
                <input
                  id="frame-enabled"
                  type="checkbox"
                  checked={frameRecipe.enabled}
                  onChange={(event) =>
                    setRecipe({ ...recipe, frame: { ...frameRecipe, enabled: event.target.checked } })
                  }
                />
                <label htmlFor="frame-enabled">Ativar moldura superior com logo e nome do canal</label>
              </div>
              <label>
                Nome do canal
                <input
                  value={frameRecipe.channel_name}
                  onChange={(event) =>
                    setRecipe({ ...recipe, frame: { ...frameRecipe, channel_name: event.target.value } })
                  }
                />
              </label>
              <label>
                Caminho da logo
                <input
                  placeholder="data/assets/logo.png"
                  value={frameRecipe.logo_path}
                  onChange={(event) =>
                    setRecipe({ ...recipe, frame: { ...frameRecipe, logo_path: event.target.value } })
                  }
                />
              </label>
              <label>
                Altura do topo (px)
                <input
                  min={80}
                  type="number"
                  value={frameRecipe.header_height}
                  onChange={(event) =>
                    setRecipe({ ...recipe, frame: { ...frameRecipe, header_height: Number(event.target.value) } })
                  }
                />
              </label>
              <label>
                Tamanho da logo (px)
                <input
                  min={40}
                  type="number"
                  value={frameRecipe.logo_size}
                  onChange={(event) =>
                    setRecipe({ ...recipe, frame: { ...frameRecipe, logo_size: Number(event.target.value) } })
                  }
                />
              </label>
              <label>
                Cor do fundo da moldura
                <input
                  value={frameRecipe.background_color}
                  onChange={(event) =>
                    setRecipe({ ...recipe, frame: { ...frameRecipe, background_color: event.target.value } })
                  }
                />
              </label>
              <label>
                Cor da linha divisória
                <input
                  value={frameRecipe.divider_color}
                  onChange={(event) =>
                    setRecipe({ ...recipe, frame: { ...frameRecipe, divider_color: event.target.value } })
                  }
                />
              </label>
              <label>
                Ajuste do vídeo
                <select
                  value={frameRecipe.video_fit || "crop"}
                  onChange={(event) =>
                    setRecipe({
                      ...recipe,
                      frame: { ...frameRecipe, video_fit: event.target.value as "crop" | "contain" | "blur_pad" }
                    })
                  }
                >
                  <option value="crop">Preencher (Crop inteligente)</option>
                  <option value="contain">Conter (Letterbox sem cortes)</option>
                  <option value="blur_pad">Fundo Desfocado (Blur Pad estilo TikTok)</option>
                </select>
              </label>
              <label>
                Espessura da linha (px)
                <input
                  min={2}
                  max={30}
                  type="number"
                  value={frameRecipe.divider_height}
                  onChange={(event) =>
                    setRecipe({ ...recipe, frame: { ...frameRecipe, divider_height: Number(event.target.value) } })
                  }
                />
              </label>
            </div>
          </div>
        </section>

        {/* ENQUADRAMENTO E EXPORT */}
        <section className="template-section">
          <div className="section-title">
            <Frame size={17} />
            <strong>Enquadramento e Export</strong>
          </div>
          <div className="form-grid three-cols">
            <label>
              Resolução Pré-definida
              <select value={activeResolution} onChange={(event) => setResolution(event.target.value)}>
                {resolutionPresets.map((preset) => (
                  <option key={preset.id} value={preset.id}>
                    {preset.label}
                  </option>
                ))}
                <option value="custom">Personalizado</option>
              </select>
            </label>
            <label>
              Largura
              <input
                min={720}
                step={2}
                type="number"
                value={recipe.format.width}
                onChange={(event) =>
                  setRecipe({ ...recipe, format: { ...recipe.format, width: Number(event.target.value) } })
                }
              />
            </label>
            <label>
              Altura
              <input
                min={1280}
                step={2}
                type="number"
                value={recipe.format.height}
                onChange={(event) =>
                  setRecipe({ ...recipe, format: { ...recipe.format, height: Number(event.target.value) } })
                }
              />
            </label>
            <label>
              Taxa de Quadros (FPS)
              <input
                min={24}
                max={60}
                type="number"
                value={recipe.format.fps || 30}
                onChange={(event) =>
                  setRecipe({ ...recipe, format: { ...recipe.format, fps: Number(event.target.value) } })
                }
              />
            </label>
            <label>
              Qualidade CRF (18 = Alta, 28 = Leve)
              <input
                max={32}
                min={16}
                type="number"
                value={recipe.export.crf}
                onChange={(event) =>
                  setRecipe({ ...recipe, export: { ...recipe.export, crf: Number(event.target.value) } })
                }
              />
            </label>
            <label>
              Velocidade de Compressão (Preset)
              <select
                value={recipe.export.preset}
                onChange={(event) => setRecipe({ ...recipe, export: { ...recipe.export, preset: event.target.value } })}
              >
                <option value="ultrafast">ultrafast (Rápido p/ testes)</option>
                <option value="veryfast">veryfast (Recomendado produção)</option>
                <option value="medium">medium (Melhor compressão)</option>
                <option value="slow">slow (Arquivamento master)</option>
              </select>
            </label>
          </div>
        </section>

        {/* TEXTOS E LEGENDAS */}
        <section className="template-section">
          <div className="section-title">
            <Captions size={17} />
            <strong>Textos e Legendas Karaokê</strong>
          </div>
          <div className="form-grid">
            <label>
              Texto Superior no Vídeo (Hook / Título)
              <textarea
                value={recipe.text.top}
                placeholder="Ex: 3 DICAS PARA VIRALIZAR HOJE"
                rows={2}
                onChange={(event) => setRecipe({ ...recipe, text: { ...recipe.text, top: event.target.value } })}
              />
            </label>
            <label>
              Texto Inferior / CTA (Chamada para Ação)
              <textarea
                value={recipe.text.bottom}
                placeholder="Ex: SIGA PARA MAIS CONTEÚDO"
                rows={2}
                onChange={(event) => setRecipe({ ...recipe, text: { ...recipe.text, bottom: event.target.value } })}
              />
            </label>
          </div>
          <div className="form-grid three-cols">
            <label>
              Tamanho da Fonte dos Textos
              <input
                max={180}
                min={36}
                type="number"
                value={recipe.text.font_size}
                onChange={(event) =>
                  setRecipe({ ...recipe, text: { ...recipe.text, font_size: Number(event.target.value) } })
                }
              />
            </label>
            <label>
              Cor do Texto
              <input
                value={recipe.text.font_color}
                onChange={(event) =>
                  setRecipe({ ...recipe, text: { ...recipe.text, font_color: event.target.value } })
                }
              />
            </label>
            <label>
              Cor da Borda/Contorno
              <input
                value={recipe.text.border_color}
                onChange={(event) =>
                  setRecipe({ ...recipe, text: { ...recipe.text, border_color: event.target.value } })
                }
              />
            </label>
          </div>

          <div className="form-grid">
            <label>
              Estilo Visual de Legenda Karaokê
              <select
                disabled={!captionRecipe.enabled}
                value={captionRecipe.style ?? "hormozi"}
                onChange={(event) =>
                  setRecipe({
                    ...recipe,
                    captions: { ...captionRecipe, style: event.target.value }
                  })
                }
              >
                <option value="hormozi">Hormozi (Destaque Amarelo Fluorescente & Borda Preta)</option>
                <option value="mrbeast">MrBeast (Komika Axis Amarelo Dourado & Tilt)</option>
                <option value="neon_cyan">Cyberpunk Neon (Ciano Elétrico & Magenta Glow)</option>
                <option value="minimalist_clean">Minimalista Clean (Off-White Suave)</option>
                <option value="bold_red">Bold Red (Impact Alerta Vermelho)</option>
              </select>
            </label>
            <label>
              Layout de Câmera / Tela
              <select
                value={recipe.layout ?? "single"}
                onChange={(event) =>
                  setRecipe({
                    ...recipe,
                    layout: event.target.value as "single" | "split_vertical" | "pip"
                  })
                }
              >
                <option value="single">Único (Vertical 9:16)</option>
                <option value="split_vertical">Split-Screen 50/50 (Câmera + Gameplay)</option>
                <option value="pip">Picture-in-Picture (PiP no canto)</option>
              </select>
            </label>
          </div>

          <div className="toggle-line">
            <input
              id="captions-enabled"
              type="checkbox"
              checked={Boolean(captionRecipe.enabled)}
              onChange={(event) =>
                setRecipe({ ...recipe, captions: { ...captionRecipe, enabled: event.target.checked } })
              }
            />
            <label htmlFor="captions-enabled">Queimar legendas dinâmicas estilo Karaokê no vídeo</label>
          </div>
          <div className="toggle-line">
            <input
              id="jumpcut-enabled"
              type="checkbox"
              checked={Boolean(recipe.jump_cut?.enabled)}
              onChange={(event) =>
                setRecipe({
                  ...recipe,
                  jump_cut: {
                    enabled: event.target.checked,
                    noise_db: recipe.jump_cut?.noise_db ?? -30,
                    min_silence_duration: recipe.jump_cut?.min_silence_duration ?? 0.4
                  }
                })
              }
            />
            <label htmlFor="jumpcut-enabled">Auto Jump-Cut (Remover silêncios e pausas mortas automaticamente)</label>
          </div>
        </section>

        {/* MÚSICA E ÁUDIO */}
        <section className="template-section">
          <div className="section-title">
            <Music2 size={17} />
            <strong>Música, Ducking e Tratamento de Áudio</strong>
          </div>
          <label>
            Trilha Sonora para Lote (Caminho ou nome do arquivo)
            <input
              placeholder="data/assets/trilha_fundo.mp3"
              value={recipe.audio.music_path ?? ""}
              onChange={(event) =>
                setRecipe({ ...recipe, audio: { ...recipe.audio, music_path: event.target.value } })
              }
            />
          </label>
          <div className="form-grid four-cols">
            <label>
              Volume da Música
              <input
                max={2}
                min={0}
                step={0.05}
                type="number"
                value={recipe.audio.music_volume ?? 0.22}
                onChange={(event) =>
                  setRecipe({ ...recipe, audio: { ...recipe.audio, music_volume: Number(event.target.value) } })
                }
              />
            </label>
            <label>
              Volume da Voz
              <input
                max={2}
                min={0}
                step={0.05}
                type="number"
                value={recipe.audio.original_volume ?? 1}
                onChange={(event) =>
                  setRecipe({ ...recipe, audio: { ...recipe.audio, original_volume: Number(event.target.value) } })
                }
              />
            </label>
            <label>
              Fade In (s)
              <input
                max={10}
                min={0}
                step={0.1}
                type="number"
                value={recipe.audio.fade_in ?? 0}
                onChange={(event) =>
                  setRecipe({ ...recipe, audio: { ...recipe.audio, fade_in: Number(event.target.value) } })
                }
              />
            </label>
            <label>
              Fade Out (s)
              <input
                max={10}
                min={0}
                step={0.1}
                type="number"
                value={recipe.audio.fade_out ?? 0}
                onChange={(event) =>
                  setRecipe({ ...recipe, audio: { ...recipe.audio, fade_out: Number(event.target.value) } })
                }
              />
            </label>
          </div>
          <div className="toggle-line">
            <input
              id="preserve-audio"
              type="checkbox"
              checked={recipe.audio.preserve}
              onChange={(event) =>
                setRecipe({ ...recipe, audio: { ...recipe.audio, preserve: event.target.checked } })
              }
            />
            <label htmlFor="preserve-audio">Preservar áudio original da voz e mixar com a música (Auto-Ducking)</label>
          </div>
          <div className="toggle-line">
            <input
              id="normalize"
              type="checkbox"
              checked={recipe.audio.normalize}
              onChange={(event) =>
                setRecipe({ ...recipe, audio: { ...recipe.audio, normalize: event.target.checked } })
              }
            />
            <label htmlFor="normalize">Normalizar volume com Loudnorm EBU R128 (-14 LUFS para redes sociais)</label>
          </div>
        </section>

        {/* WATERMARK E MARCA */}
        <section className="template-section">
          <div className="section-title">
            <ShieldCheck size={17} />
            <strong>Marca d'Água / Identidade de Canal</strong>
          </div>
          <div className="form-grid">
            <label>
              Texto da Marca d'Água
              <input
                value={recipe.watermark.text}
                placeholder="@seucanal.oficial"
                onChange={(event) =>
                  setRecipe({ ...recipe, watermark: { ...recipe.watermark, text: event.target.value } })
                }
              />
            </label>
            <label>
              Posição na Tela
              <select
                value={recipe.watermark.position}
                onChange={(event) =>
                  setRecipe({ ...recipe, watermark: { ...recipe.watermark, position: event.target.value } })
                }
              >
                <option value="bottom_right">Inferior Direito (Padrão)</option>
                <option value="bottom_left">Inferior Esquerdo</option>
                <option value="top_right">Superior Direito</option>
                <option value="top_left">Superior Esquerdo</option>
              </select>
            </label>
          </div>
          <div className="toggle-line">
            <input
              id="watermark"
              type="checkbox"
              checked={recipe.watermark.enabled}
              onChange={(event) =>
                setRecipe({ ...recipe, watermark: { ...recipe.watermark, enabled: event.target.checked } })
              }
            />
            <label htmlFor="watermark">Ativar exibição da marca d'água</label>
          </div>
        </section>
      </div>
    </section>
  );
}
