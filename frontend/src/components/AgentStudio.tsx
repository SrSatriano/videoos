import {
  AlertCircle,
  ArrowRight,
  Bot,
  Check,
  CheckCircle2,
  Clapperboard,
  Copy,
  ExternalLink,
  FileText,
  Film,
  Flame,
  Palette,
  Play,
  Send,
  Sparkles,
  Video,
  Volume2,
  Wand2
} from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "../api";
import type {
  AgentPreset,
  AgentRun,
  GeneratedScriptBlock,
  GeneratedScriptResponse,
  GenerateFacelessVideoResponse,
  TtsVoice
} from "../types";
import type { ViewKey } from "./AppShell";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";

interface AgentStudioProps {
  onNavigate?: (view: ViewKey) => void;
}

const QUICK_TOPICS = [
  "🧠 5 Hábitos Matinais de Alta Performance",
  "🚀 O Futuro da Inteligência Artificial em 2026",
  "💰 3 Segredos de Finanças que Ninguém te Conta",
  "⏳ Fatos Históricos Inacreditáveis que Parecem Ficção",
  "⚡ Truques Psicológicos de Persuasão e Lábia"
];

export function AgentStudio({ onNavigate }: AgentStudioProps) {
  const [activeTab, setActiveTab] = useState<"faceless" | "specialists">("faceless");

  // Specialists Agent state
  const [agents, setAgents] = useState<AgentPreset[]>([]);
  const [agentId, setAgentId] = useState("");
  const [brief, setBrief] = useState("Crie um roteiro curto para dica tech sobre automacao com IA.");
  const [agentResult, setAgentResult] = useState<AgentRun | null>(null);
  const [loadingAgent, setLoadingAgent] = useState(false);

  // Faceless Video Lab state
  const [topic, setTopic] = useState("5 Hábitos Matinais de Alta Performance");
  const [isGeneratingScript, setIsGeneratingScript] = useState(false);
  const [generatedScript, setGeneratedScript] = useState<GeneratedScriptResponse | null>(null);
  const [narration, setNarration] = useState("");
  const [videoName, setVideoName] = useState("");

  // Voice & TTS state
  const [voices, setVoices] = useState<TtsVoice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState("pt-BR-AntonioNeural");
  const [previewAudioUrl, setPreviewAudioUrl] = useState<string | null>(null);
  const [isPreviewingTts, setIsPreviewingTts] = useState(false);

  // Captions & Video parameters
  const [enableCaptions, setEnableCaptions] = useState(true);
  const [captionStyle, setCaptionStyle] = useState("hormozi");

  // Production execution state
  const [isProducing, setIsProducing] = useState(false);
  const [productionResult, setProductionResult] = useState<GenerateFacelessVideoResponse | null>(null);
  const [copiedPromptIndex, setCopiedPromptIndex] = useState<number | null>(null);
  const [sceneImages, setSceneImages] = useState<Record<number, { url: string; provider: string }>>({});
  const [generatingImageIndex, setGeneratingImageIndex] = useState<number | null>(null);
  const [isGeneratingAllImages, setIsGeneratingAllImages] = useState(false);
  const [allImagesProgress, setAllImagesProgress] = useState<{ current: number; total: number } | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    api.agents().then((items) => {
      setAgents(items);
      setAgentId((current) => current || items[0]?.id || "");
    });
    api.getTtsVoices().then((items) => {
      if (items && items.length > 0) {
        setVoices(items);
      }
    });
  }, []);

  // Quick submit specialist agent
  const submitAgent = async () => {
    if (!agentId || !brief.trim()) return;
    setLoadingAgent(true);
    try {
      const res = await api.runAgent({ agent_id: agentId, brief });
      setAgentResult(res);
    } finally {
      setLoadingAgent(false);
    }
  };

  // Transfer text from specialist agent to Faceless studio
  const transferAgentOutputToFaceless = () => {
    if (!agentResult?.output) return;
    setNarration(agentResult.output);
    setVideoName(`Roteiro: ${agentResult.agent.name}`);
    setActiveTab("faceless");
    setStatusMessage("Texto do agente transferido com sucesso para a narração faceless!");
  };

  // Generate structured script via Gemini / Structured LLM
  const handleGenerateScript = async (customTopic?: string) => {
    const targetTopic = (customTopic || topic).trim();
    if (!targetTopic) return;
    setIsGeneratingScript(true);
    setStatusMessage(null);
    setProductionResult(null);

    try {
      const scriptRes = await api.generateScriptToVideo(targetTopic);
      setGeneratedScript(scriptRes);
      setSceneImages({});
      setNarration(scriptRes.full_narration || "");
      setVideoName(scriptRes.title || `Vídeo IA: ${targetTopic}`);
      setStatusMessage("Roteiro estruturado gerado com sucesso via IA!");
    } catch (err: any) {
      setStatusMessage(`Erro ao gerar roteiro: ${err?.message || "Tente novamente"}`);
    } finally {
      setIsGeneratingScript(false);
    }
  };

  // Preview TTS voice sample
  const handlePreviewVoice = async () => {
    const sampleText = narration.trim().slice(0, 150) || "Olá! Este é um teste da voz neural com sincronia de legendas em tempo real.";
    setIsPreviewingTts(true);
    try {
      const res = await api.synthesizeSpeech({ text: sampleText, voice: selectedVoice });
      if (res.audio_url) {
        setPreviewAudioUrl(res.audio_url);
      } else if (res.audio_path) {
        const filename = res.audio_path.split(/[/\\]/).pop();
        setPreviewAudioUrl(`/media/tts/${filename}`);
      }
    } catch (err: any) {
      setStatusMessage(`Falha ao sintetizar áudio de prévia: ${err?.message || "Erro desconhecido"}`);
    } finally {
      setIsPreviewingTts(false);
    }
  };

  // Copy visual prompt to clipboard for image/video generation (Midjourney, Imagen, Veo)
  const handleCopyPrompt = (promptText: string, index: number) => {
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(promptText);
      setCopiedPromptIndex(index);
      setTimeout(() => setCopiedPromptIndex(null), 2500);
    }
  };

  // Generate 9:16 scene image using AI (Google Imagen 3 / Pollinations FLUX)
  const handleGenerateSceneImage = async (promptText: string, index: number) => {
    if (!promptText.trim()) return;
    setGeneratingImageIndex(index);
    try {
      const res = await api.generateSceneImage({
        prompt: promptText.trim(),
        aspect_ratio: "9:16",
        save_as_asset: true
      });
      setSceneImages((prev) => ({
        ...prev,
        [index]: { url: res.image_url, provider: res.provider }
      }));
      setStatusMessage(`Imagem da Cena #${index + 1} gerada com sucesso via ${res.provider}!`);
    } catch (err: any) {
      setStatusMessage(`Falha ao gerar imagem da cena: ${err?.message || "Erro desconhecido"}`);
    } finally {
      setGeneratingImageIndex(null);
    }
  };

  // Generate all 9:16 images in batch for all script blocks
  const handleGenerateAllImages = async () => {
    if (!generatedScript?.blocks || generatedScript.blocks.length === 0) return;
    setIsGeneratingAllImages(true);
    const blocksWithPrompts = generatedScript.blocks
      .map((b, idx) => ({ block: b, index: idx }))
      .filter((item) => item.block.visual_prompt && item.block.visual_prompt.trim().length > 0);

    const total = blocksWithPrompts.length;
    if (total === 0) {
      setStatusMessage("Nenhum prompt visual encontrado nas cenas.");
      setIsGeneratingAllImages(false);
      return;
    }

    setAllImagesProgress({ current: 0, total });
    setStatusMessage(`Iniciando geração em lote de ${total} imagens 9:16...`);

    let successCount = 0;
    for (let i = 0; i < blocksWithPrompts.length; i++) {
      const { block, index } = blocksWithPrompts[i];
      setAllImagesProgress({ current: i + 1, total });
      setGeneratingImageIndex(index);
      try {
        const res = await api.generateSceneImage({
          prompt: block.visual_prompt!.trim(),
          aspect_ratio: "9:16",
          save_as_asset: true
        });
        setSceneImages((prev) => ({
          ...prev,
          [index]: { url: res.image_url, provider: res.provider }
        }));
        successCount++;
      } catch (err: any) {
        console.error(`Erro ao gerar imagem para cena #${index + 1}:`, err);
      }
    }

    setGeneratingImageIndex(null);
    setIsGeneratingAllImages(false);
    setAllImagesProgress(null);
    setStatusMessage(`Geração concluída! ${successCount} de ${total} imagens 9:16 geradas e vinculadas às cenas.`);
  };

  // Produce Full Faceless Video (TTS + Burned SRT + Batch + Queue + Scene Images Montage)
  const handleProduceFacelessVideo = async () => {
    if (!narration.trim()) {
      setStatusMessage("Por favor, forneça ou gere o texto da narração antes de produzir o vídeo.");
      return;
    }

    setIsProducing(true);
    setStatusMessage("Sintetizando locução neural, sincronizando legendas e montando sequência visual 9:16...");

    // Passada 50/51: Injeta imagens das cenas em ordem canônica
    const orderedImages: string[] = [];
    if (generatedScript?.blocks && generatedScript.blocks.length > 0) {
      generatedScript.blocks.forEach((_, idx) => {
        if (sceneImages[idx]?.url) {
          orderedImages.push(sceneImages[idx].url);
        }
      });
    } else {
      orderedImages.push(...Object.values(sceneImages).map((i) => i.url));
    }

    try {
      const res = await api.generateFacelessVideo({
        topic,
        script_text: narration.trim(),
        voice: selectedVoice,
        enable_captions: enableCaptions,
        caption_style: captionStyle,
        video_name: videoName.trim() || undefined,
        scene_images: orderedImages.length > 0 ? orderedImages : undefined
      });

      setProductionResult(res);
      setStatusMessage("Vídeo Faceless gerado com sucesso! Lote e RenderJob enfileirados com montagem visual.");
    } catch (err: any) {
      setStatusMessage(`Erro ao produzir vídeo: ${err?.message || "Verifique os logs"}`);
    } finally {
      setIsProducing(false);
    }
  };

  const getBlockBadgeClass = (phase: string) => {
    const p = phase.toLowerCase();
    if (p.includes("hook") || p.includes("gancho")) return "hook";
    if (p.includes("context") || p.includes("contexto")) return "context";
    if (p.includes("solution") || p.includes("solu")) return "solution";
    if (p.includes("practical") || p.includes("prat")) return "practical";
    if (p.includes("cta") || p.includes("chamada")) return "cta";
    return "context";
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Top Tab Mode Navigation */}
      <nav className="faceless-mode-nav">
        <button
          type="button"
          className={`faceless-mode-btn ${activeTab === "faceless" ? "active" : ""}`}
          onClick={() => setActiveTab("faceless")}
        >
          <Sparkles size={18} />
          Estúdio Faceless &amp; Roteiros com IA
        </button>
        <button
          type="button"
          className={`faceless-mode-btn ${activeTab === "specialists" ? "active" : ""}`}
          onClick={() => setActiveTab("specialists")}
        >
          <Bot size={18} />
          Agentes Criativos Especialistas ({agents.length})
        </button>
      </nav>

      {/* Status banner */}
      {statusMessage && (
        <div
          style={{
            padding: "10px 16px",
            borderRadius: "8px",
            background: statusMessage.startsWith("Erro") ? "rgba(255, 77, 79, 0.15)" : "rgba(46, 213, 115, 0.15)",
            border: `1px solid ${statusMessage.startsWith("Erro") ? "rgba(255, 77, 79, 0.4)" : "rgba(46, 213, 115, 0.4)"}`,
            color: statusMessage.startsWith("Erro") ? "var(--red)" : "var(--green)",
            fontSize: "13px",
            display: "flex",
            alignItems: "center",
            gap: "8px"
          }}
        >
          {statusMessage.startsWith("Erro") ? <AlertCircle size={16} /> : <CheckCircle2 size={16} />}
          <span>{statusMessage}</span>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 1: FACELESS VIDEO LAB */}
      {/* ========================================================================= */}
      {activeTab === "faceless" && (
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr", gap: "20px" }}>
          {/* Left Column: Script Generation & Storyboard */}
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <Card
              eyebrow="Gerador Inteligente"
              title="Criação de Roteiro e Cenas Estruturadas"
              action={
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <span style={{ fontSize: "11px", color: "var(--muted)", background: "rgba(255,255,255,0.06)", padding: "3px 8px", borderRadius: "4px" }}>
                    Google Gemini 2.0 Flash / Ollama
                  </span>
                </div>
              }
            >
              <label style={{ fontSize: "13px", fontWeight: 600, color: "var(--text)" }}>
                Tema, Ideia ou Título do Vídeo:
              </label>
              <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
                <input
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="Ex: 5 Fatos misteriosos sobre o fundo dos oceanos"
                  style={{
                    flex: 1,
                    padding: "10px 14px",
                    borderRadius: "6px",
                    background: "rgba(0,0,0,0.3)",
                    border: "1px solid var(--border)",
                    color: "var(--text)",
                    fontSize: "13.5px"
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleGenerateScript();
                  }}
                />
                <Button
                  variant="primary"
                  label={isGeneratingScript ? "Gerando..." : "Gerar com IA"}
                  icon={<Sparkles size={16} />}
                  loading={isGeneratingScript}
                  onClick={() => handleGenerateScript()}
                />
              </div>

              {/* Quick topics chips */}
              <div className="quick-topic-chips">
                {QUICK_TOPICS.map((item, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="quick-topic-chip"
                    onClick={() => {
                      setTopic(item);
                      handleGenerateScript(item);
                    }}
                  >
                    {item}
                  </button>
                ))}
              </div>

              {/* Generated Script Overview */}
              {generatedScript && (
                <div className="script-overview-card">
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <strong style={{ fontSize: "15px", color: "#fff" }}>{generatedScript.title}</strong>
                    <span style={{ fontSize: "12px", color: "var(--yellow)", fontWeight: 600 }}>
                      <Flame size={14} style={{ display: "inline", verticalAlign: "middle", marginRight: "4px" }} />
                      Formato Retenção 9:16
                    </span>
                  </div>

                  <div className="script-meta-badges">
                    <span className="script-meta-badge">⏱️ Duração: {generatedScript.target_duration}</span>
                    <span className="script-meta-badge">📝 {generatedScript.word_count} palavras</span>
                    {generatedScript.suggested_audio_mood && (
                      <span className="script-meta-badge">🎵 Trilha: {generatedScript.suggested_audio_mood}</span>
                    )}
                  </div>

                  {generatedScript.suggested_hashtags && generatedScript.suggested_hashtags.length > 0 && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "4px" }}>
                      {generatedScript.suggested_hashtags.map((tag, tIdx) => (
                        <span key={tIdx} className="clip-hashtag-tag">
                          {tag.startsWith("#") ? tag : `#${tag}`}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Scene / Storyboard Blocks */}
              {generatedScript && generatedScript.blocks && generatedScript.blocks.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "10px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
                    <div>
                      <strong style={{ fontSize: "13.5px", color: "var(--text)" }}>
                        Estrutura das Cenas ({generatedScript.blocks.length} blocos):
                      </strong>
                      <div style={{ fontSize: "11.5px", color: "var(--muted)" }}>
                        Prompts visuais prontos para Midjourney / Imagen / Pollinations FLUX
                      </div>
                    </div>
                    <Button
                      variant="secondary"
                      compact
                      label={
                        isGeneratingAllImages
                          ? `Gerando Imagens (${allImagesProgress?.current || 0}/${allImagesProgress?.total || generatedScript.blocks.length})...`
                          : "🎨 Gerar Todas as Imagens IA"
                      }
                      icon={<Wand2 size={14} />}
                      loading={isGeneratingAllImages}
                      disabled={isGeneratingAllImages}
                      onClick={handleGenerateAllImages}
                    />
                  </div>

                  {generatedScript.blocks.map((block: GeneratedScriptBlock, index: number) => {
                    const badgeClass = getBlockBadgeClass(block.block_name || "");
                    const isCopied = copiedPromptIndex === index;

                    return (
                      <div key={index} className="script-block-card">
                        <div className="script-block-header">
                          <span className={`script-block-badge ${badgeClass}`}>
                            Cena {index + 1}: {block.block_name}
                          </span>
                          <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                            <span style={{ fontSize: "11.5px", color: "var(--muted)" }}>⏱️ {block.timing}</span>
                            {block.keyword && (
                              <span style={{ fontSize: "11.5px", color: "var(--yellow)", fontWeight: 600 }}>
                                #{block.keyword}
                              </span>
                            )}
                          </div>
                        </div>

                        <p style={{ fontSize: "13px", color: "var(--text)", margin: 0, lineHeight: 1.4 }}>
                          "{block.spoken_text}"
                        </p>

                        <div style={{ fontSize: "12px", color: "var(--muted)" }}>
                          <strong>Direção de cena:</strong> {block.visual_direction}
                        </div>

                        {block.visual_prompt && (
                          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                            <div className="script-visual-box">
                              <div style={{ display: "flex", alignItems: "center", gap: "6px", flex: 1 }}>
                                <Sparkles size={14} style={{ color: "var(--accent)", flexShrink: 0 }} />
                                <span className="script-visual-prompt-text">{block.visual_prompt}</span>
                              </div>
                              <div style={{ display: "flex", gap: "6px" }}>
                                <Button
                                  variant="secondary"
                                  compact
                                  label={generatingImageIndex === index ? "Gerando..." : "🎨 Gerar Imagem IA"}
                                  icon={<Palette size={13} />}
                                  loading={generatingImageIndex === index}
                                  onClick={() => handleGenerateSceneImage(block.visual_prompt || "", index)}
                                />
                                <Button
                                  variant="ghost"
                                  compact
                                  label={isCopied ? "Copiado!" : "Copiar"}
                                  icon={isCopied ? <Check size={13} /> : <Copy size={13} />}
                                  onClick={() => handleCopyPrompt(block.visual_prompt || "", index)}
                                />
                              </div>
                            </div>

                            {sceneImages[index] && (
                              <div style={{ display: "flex", alignItems: "center", gap: "12px", background: "rgba(0,0,0,0.3)", padding: "8px 12px", borderRadius: "8px", border: "1px solid var(--border)" }}>
                                <img
                                  src={sceneImages[index].url}
                                  alt={`Cena ${index + 1}`}
                                  style={{ width: "60px", height: "106px", objectFit: "cover", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.2)" }}
                                />
                                <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                                  <strong style={{ fontSize: "12.5px", color: "var(--text)" }}>Imagem 9:16 Gerada ({sceneImages[index].provider})</strong>
                                  <span style={{ fontSize: "11.5px", color: "var(--muted)" }}>Salva automaticamente como B-Roll na biblioteca</span>
                                  <a
                                    href={sceneImages[index].url}
                                    target="_blank"
                                    rel="noreferrer"
                                    style={{ display: "inline-flex", alignItems: "center", gap: "4px", fontSize: "11.5px", color: "var(--blue)", textDecoration: "underline" }}
                                  >
                                    <ExternalLink size={12} />
                                    Visualizar em tamanho real (1080x1920)
                                  </a>
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </Card>
          </div>

          {/* Right Column: Audio Narration & Video Production Pipeline */}
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <Card eyebrow="Locução & Render" title="Produção Faceless 9:16">
              {/* Narration editor */}
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <label style={{ fontSize: "13px", fontWeight: 600, color: "var(--text)" }}>
                    Texto para Narração Neural:
                  </label>
                  <span style={{ fontSize: "11px", color: "var(--muted)" }}>
                    {narration.length} caracteres (~{Math.round(narration.split(/\s+/).filter(Boolean).length / 2.5)}s)
                  </span>
                </div>
                <textarea
                  className="large-textarea"
                  value={narration}
                  onChange={(e) => setNarration(e.target.value)}
                  placeholder="Digite ou edite o roteiro completo que será narrado pela voz neural..."
                  style={{ minHeight: "130px", fontSize: "13px" }}
                />
              </div>

              {/* Voice Selector & Preview */}
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "12px" }}>
                <label style={{ fontSize: "13px", fontWeight: 600, color: "var(--text)" }}>
                  Voz Neural (Edge-TTS):
                </label>
                <div style={{ display: "flex", gap: "8px" }}>
                  <select
                    value={selectedVoice}
                    onChange={(e) => setSelectedVoice(e.target.value)}
                    style={{
                      flex: 1,
                      padding: "8px 12px",
                      borderRadius: "6px",
                      background: "rgba(0,0,0,0.3)",
                      border: "1px solid var(--border)",
                      color: "var(--text)",
                      fontSize: "13px"
                    }}
                  >
                    {voices.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name}
                      </option>
                    ))}
                    {voices.length === 0 && (
                      <>
                        <option value="pt-BR-AntonioNeural">Antônio (Voz Masculina pt-BR)</option>
                        <option value="pt-BR-FranciscaNeural">Francisca (Voz Feminina pt-BR)</option>
                        <option value="pt-BR-ThalitaNeural">Thalita (Voz Expressiva pt-BR)</option>
                        <option value="en-US-ChristopherNeural">Christopher (Voz Masculina en-US)</option>
                        <option value="en-US-JennyNeural">Jenny (Voz Feminina en-US)</option>
                      </>
                    )}
                  </select>
                  <Button
                    variant="secondary"
                    compact
                    label={isPreviewingTts ? "Gerando..." : "Testar Voz"}
                    icon={<Volume2 size={15} />}
                    loading={isPreviewingTts}
                    onClick={handlePreviewVoice}
                  />
                </div>

                {/* Audio preview player */}
                {previewAudioUrl && (
                  <div className="faceless-audio-bar">
                    <Volume2 size={16} style={{ color: "var(--green)" }} />
                    <audio src={previewAudioUrl} controls autoPlay />
                  </div>
                )}
              </div>

              {/* Captions Options */}
              <div
                style={{
                  background: "rgba(0,0,0,0.2)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  padding: "12px",
                  marginTop: "12px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px"
                }}
              >
                <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={enableCaptions}
                    onChange={(e) => setEnableCaptions(e.target.checked)}
                    style={{ width: "16px", height: "16px" }}
                  />
                  <strong style={{ fontSize: "13px", color: "var(--text)" }}>
                    Legendas Dinâmicas Sincronizadas
                  </strong>
                </label>

                {enableCaptions && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px", paddingLeft: "24px" }}>
                    <span style={{ fontSize: "11.5px", color: "var(--muted)" }}>Estilo Visual da Legenda:</span>
                    <select
                      value={captionStyle}
                      onChange={(e) => setCaptionStyle(e.target.value)}
                      style={{
                        padding: "6px 10px",
                        borderRadius: "6px",
                        background: "rgba(0,0,0,0.3)",
                        border: "1px solid var(--border)",
                        color: "var(--text)",
                        fontSize: "12.5px"
                      }}
                    >
                      <option value="hormozi">Hormozi (Destaque Amarelo/Verde - Alta Retenção)</option>
                      <option value="neon">Neon (Ciano/Magenta Fluorescente)</option>
                      <option value="minimal">Minimalista Clean (Branco com Sombra)</option>
                      <option value="bold_red">Bold Red (Vermelho Impacto)</option>
                    </select>
                  </div>
                )}
              </div>

              {/* Video Title */}
              <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginTop: "12px" }}>
                <label style={{ fontSize: "13px", fontWeight: 600, color: "var(--text)" }}>
                  Nome do Vídeo / Lote:
                </label>
                <input
                  type="text"
                  value={videoName}
                  onChange={(e) => setVideoName(e.target.value)}
                  placeholder="Nome do vídeo para o lote de renderização"
                  style={{
                    padding: "8px 12px",
                    borderRadius: "6px",
                    background: "rgba(0,0,0,0.3)",
                    border: "1px solid var(--border)",
                    color: "var(--text)",
                    fontSize: "13px"
                  }}
                />
              </div>

              {/* Visual Montage (B-Roll) Summary Card */}
              <div
                style={{
                  background: "rgba(0,0,0,0.2)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  padding: "12px",
                  marginTop: "12px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "8px"
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <Film size={15} style={{ color: "var(--accent)" }} />
                    <strong style={{ fontSize: "13px", color: "var(--text)" }}>Montagem Visual 9:16 (B-Rolls)</strong>
                  </div>
                  <span
                    style={{
                      fontSize: "11px",
                      fontWeight: 600,
                      padding: "2px 8px",
                      borderRadius: "12px",
                      background: Object.keys(sceneImages).length > 0 ? "rgba(16,185,129,0.15)" : "rgba(255,255,255,0.06)",
                      color: Object.keys(sceneImages).length > 0 ? "var(--green)" : "var(--muted)",
                      border: `1px solid ${Object.keys(sceneImages).length > 0 ? "rgba(16,185,129,0.3)" : "var(--border)"}`
                    }}
                  >
                    {Object.keys(sceneImages).length} imagens vinculadas
                  </span>
                </div>

                {Object.keys(sceneImages).length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    <p style={{ margin: 0, fontSize: "12px", color: "var(--text-secondary)" }}>
                      As imagens serão montadas sequencialmente cobrindo toda a duração da narração com corte de tela cheia vertical.
                    </p>
                    <div style={{ display: "flex", gap: "8px", overflowX: "auto", paddingBottom: "4px" }}>
                      {Object.entries(sceneImages).map(([idx, item]) => (
                        <div key={idx} style={{ position: "relative", flexShrink: 0 }}>
                          <img
                            src={item.url}
                            alt={`Cena ${Number(idx) + 1}`}
                            style={{
                              width: "48px",
                              height: "85px",
                              objectFit: "cover",
                              borderRadius: "4px",
                              border: "1px solid rgba(255,255,255,0.2)"
                            }}
                          />
                          <span
                            style={{
                              position: "absolute",
                              bottom: "2px",
                              right: "2px",
                              background: "rgba(0,0,0,0.75)",
                              color: "#fff",
                              fontSize: "9px",
                              padding: "1px 4px",
                              borderRadius: "2px",
                              fontWeight: 700
                            }}
                          >
                            #{Number(idx) + 1}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <p style={{ margin: 0, fontSize: "11.5px", color: "var(--muted)" }}>
                    Nenhuma imagem gerada ainda. O vídeo usará o fundo vertical padrão ou você pode gerar as imagens na coluna à esquerda com 1 clique.
                  </p>
                )}
              </div>

              {/* Main Action Button */}
              <div style={{ marginTop: "18px" }}>
                <Button
                  variant="primary"
                  label={isProducing ? "Processando e Enfileirando..." : "🚀 Produzir Vídeo Faceless 9:16"}
                  icon={<Clapperboard size={18} />}
                  loading={isProducing}
                  disabled={!narration.trim() || isProducing}
                  onClick={handleProduceFacelessVideo}
                  style={{ width: "100%", padding: "12px", fontSize: "14px", fontWeight: 700 }}
                />
              </div>

              {/* Production Success Card */}
              {productionResult && (
                <div className="faceless-success-card">
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <CheckCircle2 size={18} style={{ color: "var(--green)" }} />
                    <strong style={{ fontSize: "14px", color: "var(--green)" }}>
                      Lote Criado com Sucesso!
                    </strong>
                  </div>

                  <div style={{ fontSize: "12.5px", color: "var(--text)", display: "flex", flexDirection: "column", gap: "4px" }}>
                    <div><strong>Título:</strong> {productionResult.title}</div>
                    <div><strong>Lote ID:</strong> <code style={{ fontSize: "11.5px" }}>{productionResult.batch_id}</code></div>
                    <div><strong>Job ID:</strong> <code style={{ fontSize: "11.5px" }}>{productionResult.job_id}</code></div>
                  </div>

                  {productionResult.tts && (productionResult.tts.audio_url || productionResult.tts.audio_path) && (
                    <div>
                      <span style={{ fontSize: "11.5px", color: "var(--muted)" }}>Áudio da Locução Gerada:</span>
                      <audio
                        src={productionResult.tts.audio_url || `/media/tts/${productionResult.tts.audio_path.split(/[/\\]/).pop()}`}
                        controls
                        style={{ width: "100%", height: "32px", marginTop: "4px" }}
                      />
                    </div>
                  )}

                  {onNavigate && (
                    <Button
                      variant="secondary"
                      compact
                      label="Ver na Fila de Renderização (Lotes)"
                      icon={<ArrowRight size={15} />}
                      onClick={() => onNavigate("lotes")}
                      style={{ marginTop: "6px" }}
                    />
                  )}
                </div>
              )}
            </Card>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: SPECIALIST CREATIVE AGENTS */}
      {/* ========================================================================= */}
      {activeTab === "specialists" && (
        <section className="view-grid two-column">
          <div className="panel">
            <div className="panel-heading">
              <div>
                <h2>Agentes Especialistas</h2>
                <p>Use Gemini/Ollama com prompts especializados para Copywriting, Roteiro e SEO.</p>
              </div>
              <Bot className="ok-icon" />
            </div>

            <div className="agent-grid">
              {agents.map((agent) => (
                <button
                  className={agent.id === agentId ? "platform-button selected" : "platform-button"}
                  key={agent.id}
                  onClick={() => setAgentId(agent.id)}
                  type="button"
                >
                  <strong>{agent.name}</strong>
                  <span>{agent.role}</span>
                </button>
              ))}
            </div>

            <label style={{ fontSize: "13px", fontWeight: 600, color: "var(--text)" }}>Briefing da Tarefa:</label>
            <textarea
              className="large-textarea"
              value={brief}
              onChange={(event) => setBrief(event.target.value)}
              style={{ marginTop: "6px" }}
            />

            <Button
              variant="primary"
              compact
              disabled={loadingAgent}
              onClick={submitAgent}
              label={loadingAgent ? "Pensando..." : "Executar Agente"}
              icon={<Send size={15} />}
              style={{ marginTop: "10px" }}
            />
          </div>

          <aside className="panel">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2>Resposta do Agente</h2>
              {agentResult && agentResult.output && (
                <Button
                  variant="ghost"
                  compact
                  label="Usar no Estúdio Faceless"
                  icon={<Sparkles size={14} />}
                  onClick={transferAgentOutputToFaceless}
                />
              )}
            </div>

            <p style={{ fontSize: "12px", color: "var(--muted)", margin: "4px 0 12px 0" }}>
              {agentResult
                ? `${agentResult.agent.name} via ${agentResult.provider}${agentResult.model ? ` (${agentResult.model})` : ""}`
                : "Aguardando execução do briefing."}
            </p>

            <pre className="agent-output" style={{ fontSize: "13px" }}>
              {agentResult?.output ?? "Escolha um especialista ao lado e envie as instruções."}
            </pre>
          </aside>
        </section>
      )}
    </div>
  );
}
