import { AudioLines, Music2, SlidersHorizontal, Wand2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { api } from "../api";
import type { MusicBrief, MusicStatus } from "../types";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";

export function MusicLab() {
  const [prompt, setPrompt] = useState("trilha tech futurista para tutorial rapido");
  const [ducking, setDucking] = useState(65);
  const [status, setStatus] = useState<MusicStatus | null>(null);
  const fallbackBrief = useMemo(() => {
    const mood = prompt.toLowerCase().includes("tech") || prompt.toLowerCase().includes("futur") ? "tech" : "creator";
    return { mood, bpm: mood === "tech" ? 120 : 96, description: prompt, rights_note: "Use trilhas proprias ou licenciadas." };
  }, [prompt]);
  const [brief, setBrief] = useState<MusicBrief | null>(null);
  const currentBrief = brief ?? fallbackBrief;
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    api.musicStatus().then(setStatus);
  }, []);
  const generateBrief = async () => {
    try {
      setLoading(true);
      setBrief(await api.musicBrief({ prompt }));
    } catch (err) {
      // Ignora graciosamente falhas de conexão
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="view-grid two-column">
      <Card
        title="Music Lab"
        eyebrow="estilo Suno, local-first"
        action={<Button compact loading={loading} icon={<Wand2 size={16} />} label="Gerar brief" onClick={generateBrief} />}
      >
        <label>
          Vibe da trilha
          <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} />
        </label>
        <div className="music-brief">
          <Music2 size={22} />
          <div>
            <strong>{currentBrief.mood.toUpperCase()} - {currentBrief.bpm} BPM</strong>
            <span>{currentBrief.rights_note}</span>
          </div>
        </div>
        <label>
          Ducking da musica quando houver voz: {ducking}%
          <input max={100} min={0} type="range" value={ducking} onChange={(event) => setDucking(Number(event.target.value))} />
        </label>
        <div className="command-actions left">
          <Button icon={<AudioLines size={17} />} label="Importar audio" onClick={() => undefined} />
          <Button icon={<SlidersHorizontal size={17} />} label="Extrair stems" onClick={() => undefined} />
        </div>
      </Card>

      <Card title="Stems" eyebrow="opcional">
        <p>{status?.message ?? "Checando engine de stems..."}</p>
        <div className="stem-grid">
          {["vocals", "drums", "bass", "other", "instrumental"].map((stem) => (
            <button className="stem-card" key={stem} type="button">
              <AudioLines size={20} />
              <span>{stem}</span>
              <small>{status?.demucs_available ? "disponivel" : "pendente"}</small>
            </button>
          ))}
        </div>
      </Card>
    </section>
  );
}
