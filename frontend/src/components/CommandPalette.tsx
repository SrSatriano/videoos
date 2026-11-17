import {
  Activity,
  Archive,
  Bot,
  CalendarDays,
  Captions,
  Clapperboard,
  Database,
  Download,
  Film,
  Home,
  Layers3,
  Music2,
  PackageCheck,
  Palette,
  PlaySquare,
  RefreshCw,
  Scissors,
  Search,
  SlidersHorizontal,
  Sparkles,
  X
} from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { ViewKey } from "./AppShell";

interface CommandItem {
  id: string;
  title: string;
  category: "Navegação" | "Ações Rápidas";
  icon: ReactNode;
  hint?: string;
  action: () => void;
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (view: ViewKey) => void;
  onRefresh: () => void;
  onBackup: () => void;
}

export function CommandPalette({
  isOpen,
  onClose,
  onNavigate,
  onRefresh,
  onBackup
}: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const commands: CommandItem[] = useMemo(
    () => [
      {
        id: "nav-home",
        title: "Mesa de Produção (Home)",
        category: "Navegação",
        icon: <Home size={18} />,
        hint: "Visão geral e métricas",
        action: () => onNavigate("home")
      },
      {
        id: "nav-biblioteca",
        title: "Media Pool (Biblioteca de Vídeos)",
        category: "Navegação",
        icon: <Film size={18} />,
        hint: "Assets brutos, filtros e importação",
        action: () => onNavigate("biblioteca")
      },
      {
        id: "nav-captura",
        title: "MassLoader (Captura Social)",
        category: "Navegação",
        icon: <Download size={18} />,
        hint: "Download em massa do Instagram/YouTube",
        action: () => onNavigate("captura")
      },
      {
        id: "nav-clips",
        title: "AI Clips (Cortes Automáticos)",
        category: "Navegação",
        icon: <Sparkles size={18} />,
        hint: "Destaques inteligentes e hooks",
        action: () => onNavigate("clips")
      },
      {
        id: "nav-templates",
        title: "Template Studio (Receitas 9:16)",
        category: "Navegação",
        icon: <SlidersHorizontal size={18} />,
        hint: "Edição de molduras, canais e legendas",
        action: () => onNavigate("templates")
      },
      {
        id: "nav-lotes",
        title: "Fila de Render (Lotes de Vídeos)",
        category: "Navegação",
        icon: <Layers3 size={18} />,
        hint: "Criação de lotes, pausa, retry e status",
        action: () => onNavigate("lotes")
      },
      {
        id: "nav-revisao",
        title: "Review Bay (Revisão Técnica e Safe Zones)",
        category: "Navegação",
        icon: <PlaySquare size={18} />,
        hint: "QC, loudness, aprovação editorial e player",
        action: () => onNavigate("revisao")
      },
      {
        id: "nav-publicacao",
        title: "Publish Desk (Pacotes de Publicação)",
        category: "Navegação",
        icon: <PackageCheck size={18} />,
        hint: "Checklist, legendas, tags e relatórios v2",
        action: () => onNavigate("publicacao")
      },
      {
        id: "nav-transcricao",
        title: "Caption Lab (Transcrição e Legendas)",
        category: "Navegação",
        icon: <Captions size={18} />,
        hint: "Whisper, exportação SRT/VTT e vícios de linguagem",
        action: () => onNavigate("transcricao")
      },
      {
        id: "nav-musica",
        title: "Music Lab (Áudio e Stems)",
        category: "Navegação",
        icon: <Music2 size={18} />,
        hint: "Briefs de áudio, trilhas e ducking",
        action: () => onNavigate("musica")
      },
      {
        id: "nav-broll",
        title: "B-roll Desk",
        category: "Navegação",
        icon: <Clapperboard size={18} />,
        hint: "Inserção de apoios visuais",
        action: () => onNavigate("broll")
      },
      {
        id: "nav-marca",
        title: "Brand Kit Studio",
        category: "Navegação",
        icon: <Palette size={18} />,
        hint: "Logos, fontes e cores de canais",
        action: () => onNavigate("marca")
      },
      {
        id: "nav-calendario",
        title: "Calendário de Postagens",
        category: "Navegação",
        icon: <CalendarDays size={18} />,
        hint: "Planejamento editorial semanal",
        action: () => onNavigate("calendario")
      },
      {
        id: "nav-ferramentas",
        title: "Editor Tools (Ferramentas de Edição)",
        category: "Navegação",
        icon: <Scissors size={18} />,
        hint: "Proxies, detecção de cenas e marcadores",
        action: () => onNavigate("ferramentas")
      },
      {
        id: "nav-presets",
        title: "Biblioteca de Presets",
        category: "Navegação",
        icon: <Archive size={18} />,
        hint: "Templates, filtros, máscaras e estilos de legenda",
        action: () => onNavigate("presets")
      },
      {
        id: "nav-agentes",
        title: "Agent Studio (Agentes de IA)",
        category: "Navegação",
        icon: <Bot size={18} />,
        hint: "Roteiros, hooks, SEO e ideias com LLM local",
        action: () => onNavigate("agentes")
      },
      {
        id: "nav-sistema",
        title: "Painel do Sistema & Integridade",
        category: "Navegação",
        icon: <Activity size={18} />,
        hint: "Saúde, logs de auditoria e configurações",
        action: () => onNavigate("sistema")
      },
      {
        id: "action-backup",
        title: "Criar Backup do Banco de Dados",
        category: "Ações Rápidas",
        icon: <Database size={18} />,
        hint: "Copia SQLite com manifesto em data/db/",
        action: onBackup
      },
      {
        id: "action-refresh",
        title: "Atualizar Dados do Sistema",
        category: "Ações Rápidas",
        icon: <RefreshCw size={18} />,
        hint: "Recarrega fila, assets e métricas",
        action: onRefresh
      }
    ],
    [onNavigate, onRefresh, onBackup]
  );

  const filteredCommands = useMemo(() => {
    if (!query.trim()) return commands;
    const lower = query.toLowerCase();
    return commands.filter(
      (cmd) =>
        cmd.title.toLowerCase().includes(lower) ||
        cmd.category.toLowerCase().includes(lower) ||
        (cmd.hint && cmd.hint.toLowerCase().includes(lower))
    );
  }, [commands, query]);

  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev < filteredCommands.length - 1 ? prev + 1 : 0));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : filteredCommands.length - 1));
      } else if (e.key === "Enter" && filteredCommands.length > 0) {
        e.preventDefault();
        const selected = filteredCommands[selectedIndex];
        if (selected) {
          selected.action();
          onClose();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, selectedIndex, filteredCommands, onClose]);

  if (!isOpen) return null;

  return (
    <div className="command-palette-backdrop" onClick={onClose}>
      <div className="command-palette-modal" onClick={(e) => e.stopPropagation()}>
        <div className="command-palette-header">
          <Search size={18} className="command-palette-icon" />
          <input
            ref={inputRef}
            type="text"
            className="command-palette-input"
            placeholder="Digite um comando ou tela... (Ctrl+K para fechar)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button className="command-palette-close" onClick={onClose} aria-label="Fechar">
            <X size={16} />
          </button>
        </div>

        <div className="command-palette-body">
          {filteredCommands.length === 0 ? (
            <div className="command-palette-empty">Nenhum comando encontrado para "{query}"</div>
          ) : (
            <ul className="command-palette-list">
              {filteredCommands.map((cmd, index) => (
                <li
                  key={cmd.id}
                  className={`command-palette-item ${index === selectedIndex ? "selected" : ""}`}
                  onClick={() => {
                    cmd.action();
                    onClose();
                  }}
                  onMouseEnter={() => setSelectedIndex(index)}
                >
                  <span className="command-item-icon">{cmd.icon}</span>
                  <div className="command-item-content">
                    <span className="command-item-title">{cmd.title}</span>
                    {cmd.hint && <span className="command-item-hint">{cmd.hint}</span>}
                  </div>
                  <span className="command-item-category">{cmd.category}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="command-palette-footer">
          <span>
            <kbd>↑</kbd> <kbd>↓</kbd> para navegar
          </span>
          <span>
            <kbd>Enter</kbd> para selecionar
          </span>
          <span>
            <kbd>Esc</kbd> para fechar
          </span>
        </div>
      </div>
    </div>
  );
}
