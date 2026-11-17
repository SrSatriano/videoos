import { Film, Plus, Wand2 } from "lucide-react";
import { useState } from "react";

import { api } from "../api";
import type { BrollCue } from "../types";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";

export function BrollDesk() {
  const [text, setText] = useState("abre o Instagram e automatiza as respostas");
  const [keywords, setKeywords] = useState("instagram, automacao, dashboard, celular");
  const [cues, setCues] = useState<BrollCue[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  const suggest = async () => {
    try {
      const result = await api.suggestBroll({
        segments: [{ start: 0, end: 6, text }],
        local_asset_keywords: keywords
          .split(",")
          .map((keyword) => keyword.trim())
          .filter(Boolean)
      });
      setCues(result.cues);
      setMessage(`${result.cues.length} sugestao(oes) encontrada(s).`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Falha ao sugerir b-roll.");
    }
  };

  return (
    <section className="view-grid two-column">
      <Card
        title="B-roll Desk"
        eyebrow="apoio visual"
        action={<Button compact icon={<Wand2 size={16} />} label="Sugerir" onClick={suggest} variant="primary" />}
      >
        <label>
          Trecho da transcricao
          <textarea className="large-textarea" value={text} onChange={(event) => setText(event.target.value)} />
        </label>
        <label>
          Keywords dos assets locais
          <input value={keywords} onChange={(event) => setKeywords(event.target.value)} />
        </label>
        <div className="rule-list">
          <span>match por keyword</span>
          <span>sem banco externo</span>
          <span>aplicacao manual</span>
          <span>pronto para overlay</span>
        </div>
        {message ? <p className="inline-error">{message}</p> : null}
      </Card>

      <Card title="Sugestoes" eyebrow="timeline">
        <div className="clip-candidate-list">
          {cues.map((cue, index) => (
            <article className="clip-candidate" key={`${cue.keyword}-${index}`}>
              <div className="score-ring">
                <Film size={18} />
              </div>
              <div>
                <strong>{cue.keyword}</strong>
                <span>{cue.start_seconds}s - {cue.end_seconds}s</span>
                <small>{cue.prompt}</small>
              </div>
              <Button compact icon={<Plus size={15} />} label="Usar" onClick={() => undefined} />
            </article>
          ))}
          {cues.length === 0 ? <div className="empty-state">Gere sugestoes a partir de um trecho.</div> : null}
        </div>
      </Card>
    </section>
  );
}
