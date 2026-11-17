import { Palette, Save, Type } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "../api";
import type { BrandKit } from "../types";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";
import { SegmentedControl } from "./ui/SegmentedControl";

type CaptionMode = "bold" | "karaoke" | "minimal";

export function BrandKitStudio() {
  const [captionMode, setCaptionMode] = useState<CaptionMode>("bold");
  const [primary, setPrimary] = useState("#51d88a");
  const [accent, setAccent] = useState("#4da3ff");
  const [cta, setCta] = useState("Comenta \"eu quero\" para receber");
  const [name, setName] = useState("Dicas Tech");
  const [kits, setKits] = useState<BrandKit[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.brandKits().then(setKits);
  }, []);

  const save = async () => {
    try {
      setSaving(true);
      const kit = await api.createBrandKit({
        name,
        is_default: true,
        config: {
          colors: { primary, accent, text: "#ffffff", outline: "#050607" },
          caption: { mode: captionMode, font_size: 74, position: "bottom" },
          cta: { text: cta, position: "final" }
        }
      });
      setMessage(`Brand Kit salvo: ${kit.name}`);
      setKits(await api.brandKits());
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Falha ao salvar Brand Kit.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="view-grid brand-layout">
      <Card
        title="Brand Kit"
        eyebrow="identidade"
        action={<Button compact loading={saving} icon={<Save size={16} />} label="Salvar" onClick={save} variant="primary" />}
      >
        <label>
          Nome
          <input value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <div className="form-grid">
          <label>
            Cor principal
            <input type="color" value={primary} onChange={(event) => setPrimary(event.target.value)} />
          </label>
          <label>
            Cor de destaque
            <input type="color" value={accent} onChange={(event) => setAccent(event.target.value)} />
          </label>
        </div>
        <label>
          CTA padrao
          <input value={cta} onChange={(event) => setCta(event.target.value)} />
        </label>
        <label>
          Estilo de captions
          <SegmentedControl
            label="Estilo de captions"
            onChange={setCaptionMode}
            options={[
              { label: "Bold", value: "bold" },
              { label: "Karaoke", value: "karaoke" },
              { label: "Minimal", value: "minimal" }
            ]}
            value={captionMode}
          />
        </label>
        <div className="brand-swatches">
          <span style={{ background: primary }} />
          <span style={{ background: accent }} />
          <span style={{ background: "#ffd166" }} />
          <span style={{ background: "#f2f5f7" }} />
        </div>
        {message ? <p className="inline-error">{message}</p> : null}
      </Card>

      <Card title="Preview 9:16" eyebrow="safe area">
        <div className={`preview-phone caption-${captionMode}`}>
          <div className="brand-watermark">@sistema.dark</div>
          <Palette size={44} />
          <div className="caption-preview" style={{ borderColor: accent }}>
            <Type size={18} />
            <span>{cta}</span>
          </div>
        </div>
        <div className="task-list brand-kit-list">
          {kits.map((kit) => (
            <button
              className="task-row"
              key={kit.id}
              onClick={() => {
                setName(kit.name);
                const colors = kit.config.colors as { primary?: string; accent?: string } | undefined;
                const ctaConfig = kit.config.cta as { text?: string } | undefined;
                if (colors?.primary) setPrimary(colors.primary);
                if (colors?.accent) setAccent(colors.accent);
                if (ctaConfig?.text) setCta(ctaConfig.text);
              }}
              type="button"
            >
              <div>
                <strong>{kit.name}</strong>
                <span>{kit.is_default ? "padrao" : "alternativo"}</span>
              </div>
            </button>
          ))}
        </div>
      </Card>
    </section>
  );
}
