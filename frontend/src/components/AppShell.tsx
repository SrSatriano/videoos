import {
  Activity,
  Archive,
  Bot,
  CalendarDays,
  Captions,
  ChevronDown,
  Clapperboard,
  Database,
  Download,
  Film,
  FileVideo,
  Home,
  Layers3,
  Menu,
  Music2,
  PackageCheck,
  Palette,
  PlaySquare,
  Rocket,
  Scissors,
  Search,
  SlidersHorizontal,
  Sparkles,
  Upload,
  X
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import type { RenderJob } from "../types";

export type ViewKey =
  | "home"
  | "biblioteca"
  | "clips"
  | "broll"
  | "ferramentas"
  | "presets"
  | "marca"
  | "templates"
  | "lotes"
  | "revisao"
  | "publicacao"
  | "agentes"
  | "captura"
  | "transcricao"
  | "musica"
  | "calendario"
  | "sistema";

const viewMeta: Record<ViewKey, { title: string; subtitle: string; accent: string }> = {
  home: {
    title: "Mesa de Producao",
    subtitle: "Visao geral do pipeline local: importar, cortar, renderizar, revisar e empacotar.",
    accent: "Studio"
  },
  biblioteca: {
    title: "Media Pool",
    subtitle: "Importe videos, encontre duplicados e prepare material bruto para lotes.",
    accent: "Ingest"
  },
  clips: {
    title: "AI Clips",
    subtitle: "Sugira cortes, hooks e lotes derivados para shorts verticais.",
    accent: "Cut"
  },
  broll: {
    title: "B-roll Desk",
    subtitle: "Monte apoios visuais por trecho e prepare overlays para o render.",
    accent: "Overlay"
  },
  ferramentas: {
    title: "Editor Tools",
    subtitle: "Proxies, deteccao de cenas, marcadores e presets de exportacao local.",
    accent: "Tools"
  },
  presets: {
    title: "Biblioteca de Presets",
    subtitle: "Templates, filtros, mascaras e estilos de legenda para edicao em massa.",
    accent: "Looks"
  },
  marca: {
    title: "Brand Kit",
    subtitle: "Cores, CTA, watermark e identidade visual dos canais.",
    accent: "Brand"
  },
  templates: {
    title: "Template Studio",
    subtitle: "Receitas reutilizaveis de edicao, captions, b-roll e exportacao.",
    accent: "Recipes"
  },
  lotes: {
    title: "Fila de Render",
    subtitle: "Crie lotes, acompanhe progresso e recupere jobs persistidos.",
    accent: "Queue"
  },
  revisao: {
    title: "Review Bay",
    subtitle: "Assista, aprove, reprove e baixe renders finais.",
    accent: "QC"
  },
  publicacao: {
    title: "Publish Desk",
    subtitle: "Gere pastas prontas para Instagram, TikTok e YouTube Shorts.",
    accent: "Ship"
  },
  agentes: {
    title: "Agent Studio",
    subtitle: "Roteiros, hooks, SEO, QA e ideias com agentes locais.",
    accent: "AI"
  },
  captura: {
    title: "MassLoader",
    subtitle: "Baixe conteudo publico/autorizado e importe direto para a biblioteca.",
    accent: "Capture"
  },
  transcricao: {
    title: "Caption Lab",
    subtitle: "Transcreva, revise, exporte SRT/VTT e detecte vicios de fala.",
    accent: "Text"
  },
  musica: {
    title: "Music Lab",
    subtitle: "Briefs de trilha, moods, stems opcionais e ducking de voz.",
    accent: "Audio"
  },
  calendario: {
    title: "Calendario",
    subtitle: "Planeje a semana de publicacao manual por plataforma.",
    accent: "Plan"
  },
  sistema: {
    title: "Sistema e Backups",
    subtitle: "Saude local, SQLite, FFmpeg, auditoria e backups.",
    accent: "Local"
  }
};

const navGroups: Array<{ label: string; items: Array<{ key: ViewKey; label: string; icon: ReactNode }> }> = [
  {
    label: "Fluxo",
    items: [
      { key: "home", label: "Home", icon: <Home size={18} /> },
      { key: "biblioteca", label: "Biblioteca", icon: <FileVideo size={18} /> },
      { key: "captura", label: "Captura", icon: <Download size={18} /> },
      { key: "transcricao", label: "Transcricao", icon: <Captions size={18} /> }
    ]
  },
  {
    label: "Edicao",
    items: [
      { key: "clips", label: "AI Clips", icon: <Sparkles size={18} /> },
      { key: "broll", label: "B-roll", icon: <Film size={18} /> },
      { key: "ferramentas", label: "Editor Tools", icon: <Scissors size={18} /> },
      { key: "presets", label: "Presets", icon: <SlidersHorizontal size={18} /> },
      { key: "templates", label: "Templates", icon: <Layers3 size={18} /> },
      { key: "marca", label: "Brand Kit", icon: <Palette size={18} /> },
      { key: "musica", label: "Music Lab", icon: <Music2 size={18} /> }
    ]
  },
  {
    label: "Entrega",
    items: [
      { key: "lotes", label: "Lotes", icon: <Clapperboard size={18} /> },
      { key: "revisao", label: "Revisao", icon: <PlaySquare size={18} /> },
      { key: "publicacao", label: "Publicacao", icon: <PackageCheck size={18} /> },
      { key: "calendario", label: "Calendario", icon: <CalendarDays size={18} /> }
    ]
  },
  {
    label: "Controle",
    items: [
      { key: "agentes", label: "Agentes", icon: <Bot size={18} /> },
      { key: "sistema", label: "Configurações", icon: <SlidersHorizontal size={18} /> }
    ]
  }
];

const workflowItems: Array<{ key: ViewKey; label: string }> = [
  { key: "biblioteca", label: "01 Ingest" },
  { key: "clips", label: "02 Corte" },
  { key: "templates", label: "03 Look" },
  { key: "lotes", label: "04 Render" },
  { key: "revisao", label: "05 Review" },
  { key: "publicacao", label: "06 Pack" }
];

interface AppShellProps {
  activeView: ViewKey;
  onViewChange: (view: ViewKey) => void;
  onImport: () => void;
  onNewBatch: () => void;
  onProcessNext: () => void;
  onOpenCommandPalette?: () => void;
  children: ReactNode;
  isApiOnline: boolean;
  jobs?: RenderJob[];
}

export function AppShell({
  activeView,
  onViewChange,
  onImport,
  onNewBatch,
  onProcessNext,
  onOpenCommandPalette,
  children,
  isApiOnline,
  jobs = []
}: AppShellProps) {
  const meta = viewMeta[activeView];
  const activeGroupLabel = navGroups.find((group) => group.items.some((item) => item.key === activeView))?.label;
  const [openGroups, setOpenGroups] = useState<Set<string>>(
    () => new Set(["Fluxo", ...(activeGroupLabel ? [activeGroupLabel] : [])])
  );
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [showMiniQueue, setShowMiniQueue] = useState(false);

  const activeJob = jobs.find((j) => j.status === "processing");
  const queuedJobs = jobs.filter((j) => j.status === "queued");

  useEffect(() => {
    if (!activeGroupLabel) return;
    setOpenGroups((current) => {
      if (current.has(activeGroupLabel)) return current;
      return new Set([...current, activeGroupLabel]);
    });
  }, [activeGroupLabel]);

  useEffect(() => {
    setMobileNavOpen(false);
  }, [activeView]);

  const toggleGroup = (label: string) => {
    setOpenGroups((current) => {
      const next = new Set(current);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  };

  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-to-content">
        Pular para o conteúdo principal
      </a>
      <aside className={mobileNavOpen ? "sidebar mobile-open" : "sidebar"}>
        <div className="mobile-sidebar-head">
          <div className="brand-block">
            <div className="brand-mark">
              <Rocket size={22} />
            </div>
            <div>
              <strong>Video OS</strong>
              <span>desktop creator suite</span>
            </div>
          </div>
          <button
            className="icon-button mobile-nav-toggle"
            type="button"
            onClick={() => setMobileNavOpen((current) => !current)}
            aria-controls="video-os-navigation"
            aria-expanded={mobileNavOpen}
            aria-label={mobileNavOpen ? "Fechar navegacao" : "Abrir navegacao"}
            title={mobileNavOpen ? "Fechar navegacao" : "Abrir navegacao"}
          >
            {mobileNavOpen ? <X size={19} /> : <Menu size={19} />}
          </button>
        </div>
        <div className="sidebar-status">
          <Activity size={15} />
          <span>{isApiOnline ? "Sistema local online" : "Aguardando API"}</span>
        </div>

        <nav className="nav-list" id="video-os-navigation" aria-label="Fluxo principal">
          {navGroups.map((group) => (
            <section className={openGroups.has(group.label) ? "nav-group open" : "nav-group"} key={group.label}>
              <button
                className="nav-group-toggle"
                type="button"
                onClick={() => toggleGroup(group.label)}
                aria-expanded={openGroups.has(group.label)}
              >
                <span>{group.label}</span>
                <ChevronDown size={14} />
              </button>
              <div className="nav-group-items">
                {group.items.map((item) => (
                  <button
                    key={item.key}
                    className={item.key === activeView ? "nav-item active" : "nav-item"}
                    onClick={() => {
                      onViewChange(item.key);
                      setMobileNavOpen(false);
                    }}
                    type="button"
                    aria-current={item.key === activeView ? "page" : undefined}
                    title={item.label}
                  >
                    {item.icon}
                    <span>{item.label}</span>
                  </button>
                ))}
              </div>
            </section>
          ))}
        </nav>

        <div className="sidebar-footer">
          <Database size={16} />
          <span>{isApiOnline ? "Local-first ativo" : "API offline"}</span>
        </div>
      </aside>

      <main className="workspace" id="main-content" tabIndex={-1}>
        <header className="command-bar">
          <div>
            <span className="workspace-accent">{meta.accent}</span>
            <h1>{meta.title}</h1>
            <p>{meta.subtitle}</p>
          </div>
          <div className="command-actions">
            {onOpenCommandPalette && (
              <button
                className="secondary-button"
                onClick={onOpenCommandPalette}
                type="button"
                title="Abrir Command Palette (Ctrl+K)"
                aria-label="Abrir Command Palette (Ctrl+K)"
              >
                <Search size={16} />
                Comandos
              </button>
            )}
            <div className="mini-queue-wrapper">
              <button
                className={`secondary-button mini-queue-trigger ${activeJob ? "rendering" : ""}`}
                onClick={() => setShowMiniQueue((prev) => !prev)}
                type="button"
                title="Acompanhar Fila e Lotes (Mini-Queue HUD)"
                aria-expanded={showMiniQueue}
                aria-haspopup="dialog"
                aria-label={`Mini-Queue HUD: ${activeJob ? `Renderizando (${activeJob.progress}%)` : `${queuedJobs.length} jobs na fila`}`}
              >
                <Activity size={16} className={activeJob ? "pulse-anim text-green" : ""} />
                <span>{activeJob ? `Render (${activeJob.progress}%)` : `${queuedJobs.length} na fila`}</span>
              </button>

              {showMiniQueue && (
                <div className="mini-queue-popover">
                  <div className="mini-queue-popover-head">
                    <strong>Fila de Renderização</strong>
                    <span className="mini-queue-badge">{jobs.length} jobs</span>
                  </div>
                  {activeJob ? (
                    <div className="mini-queue-active-card">
                      <div className="mini-queue-row">
                        <span className="mini-pulse-dot" />
                        <strong className="truncate">{activeJob.asset_filename || activeJob.asset_id.slice(0, 8)}</strong>
                      </div>
                      <span className="mini-queue-step">{activeJob.current_step} — {activeJob.progress}%</span>
                      <div className="progress-track">
                        <span style={{ width: `${Math.max(5, activeJob.progress)}%` }} />
                      </div>
                    </div>
                  ) : (
                    <div className="mini-queue-empty">
                      <span>Nenhum render em processamento no momento.</span>
                    </div>
                  )}

                  {queuedJobs.length > 0 && (
                    <div className="mini-queue-queued-list">
                      <span className="mini-queue-subhead">Aguardando slot ({queuedJobs.length}):</span>
                      {queuedJobs.slice(0, 3).map((job) => (
                        <div key={job.id} className="mini-queue-queued-item">
                          <span className="truncate">{job.asset_filename || job.asset_id.slice(0, 8)}</span>
                          <span className="status-pill status-queued">Pendente</span>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="mini-queue-popover-foot">
                    <button
                      className="secondary-button compact"
                      onClick={() => {
                        onViewChange("lotes");
                        setShowMiniQueue(false);
                      }}
                      type="button"
                    >
                      Abrir Fila
                    </button>
                    <button
                      className="primary-button compact"
                      onClick={() => {
                        onProcessNext();
                      }}
                      type="button"
                    >
                      Processar 1
                    </button>
                  </div>
                </div>
              )}
            </div>

            <button className="secondary-button" onClick={onImport} type="button">
              <Upload size={17} />
              Importar
            </button>
            <button className="secondary-button" onClick={onNewBatch} type="button">
              <Clapperboard size={17} />
              Novo lote
            </button>
            <button className="primary-button" onClick={onProcessNext} type="button">
              <PlaySquare size={17} />
              Renderizar
            </button>
          </div>
        </header>

        {activeJob ? (
          <div className="global-render-banner" role="progressbar" aria-valuenow={activeJob.progress} aria-valuemin={0} aria-valuemax={100}>
            <div className="global-render-fill" style={{ width: `${Math.max(4, activeJob.progress)}%` }} />
            <div className="global-render-content">
              <Activity size={14} className="pulse-anim text-green" />
              <span>
                <strong>Renderizando:</strong> {activeJob.asset_filename || activeJob.asset_id.slice(0, 8)} ({activeJob.progress}%) · {activeJob.current_step}
              </span>
            </div>
          </div>
        ) : null}
        {activeView === "home" ? (
          <div className="workflow-strip" aria-label="Fluxo rapido">
            {workflowItems.map((item) => (
              <button
                className={activeView === item.key ? "workflow-step active" : "workflow-step"}
                key={item.key}
                onClick={() => onViewChange(item.key)}
                type="button"
              >
                {item.label}
              </button>
            ))}
          </div>
        ) : null}
        {children}
      </main>
    </div>
  );
}
