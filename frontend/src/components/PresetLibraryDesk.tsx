import { Captions, Layers3, Palette, SlidersHorizontal } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "../api";
import type { PresetLibrary } from "../types";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";

export function PresetLibraryDesk() {
  const [library, setLibrary] = useState<PresetLibrary | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    api.presetLibrary().then(setLibrary);
  }, []);

  const install = async (presetId: string) => {
    try {
      const template = await api.installTemplatePreset(presetId);
      setMessage(`Template instalado: ${template.name}`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Falha ao instalar template.");
    }
  };

  if (!library) {
    return <div className="empty-state">Carregando biblioteca de presets...</div>;
  }

  return (
    <section className="view-grid preset-layout">
      <Card title="Biblioteca massiva" eyebrow="templates, filtros, mascaras e legendas">
        <div className="quick-grid">
          <div className="quick-card static">
            <Layers3 size={20} />
            <span>Templates</span>
            <strong>{library.counts.templates}</strong>
          </div>
          <div className="quick-card static">
            <SlidersHorizontal size={20} />
            <span>Filtros</span>
            <strong>{library.counts.filters}</strong>
          </div>
          <div className="quick-card static">
            <Palette size={20} />
            <span>Mascaras</span>
            <strong>{library.counts.masks}</strong>
          </div>
          <div className="quick-card static">
            <Captions size={20} />
            <span>Legendas</span>
            <strong>{library.counts.captions}</strong>
          </div>
        </div>
        {message ? <p className="inline-error">{message}</p> : null}
        <div className="template-list preset-list">
          {library.templates.slice(0, 50).map((template) => (
            <article className="template-row preset-row" key={template.id}>
              <Layers3 size={18} />
              <span>
                <strong>{template.name}</strong>
                <small>{template.description}</small>
              </span>
              <Button compact label="Instalar" onClick={() => install(template.id)} />
            </article>
          ))}
        </div>
      </Card>

      <Card title="Filtros, mascaras e captions" eyebrow="base estilo editor">
        <div className="preset-columns">
          <div>
            <h3>100 filtros</h3>
            {library.filters.slice(0, 12).map((filter) => (
              <code key={filter.id}>{filter.name}</code>
            ))}
          </div>
          <div>
            <h3>100 mascaras</h3>
            {library.masks.slice(0, 12).map((mask) => (
              <code key={mask.id}>{mask.name}</code>
            ))}
          </div>
          <div>
            <h3>50 legendas</h3>
            {library.captions.slice(0, 12).map((caption) => (
              <code key={caption.id}>{caption.name}</code>
            ))}
          </div>
        </div>
      </Card>
    </section>
  );
}
