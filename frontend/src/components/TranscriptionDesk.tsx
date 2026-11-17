import { Captions, FileText, Subtitles, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "../api";
import type { Asset, Transcript, TranscriptionResult, TranscriptionStatus } from "../types";
import { Button } from "./ui/Button";

interface TranscriptionDeskProps {
  assets: Asset[];
  onDeleteAssets: (assetIds: string[]) => void;
}

export function TranscriptionDesk({ assets, onDeleteAssets }: TranscriptionDeskProps) {
  const [status, setStatus] = useState<TranscriptionStatus | null>(null);
  const [assetId, setAssetId] = useState("");
  const [result, setResult] = useState<TranscriptionResult | null>(null);
  const [transcripts, setTranscripts] = useState<Transcript[]>([]);
  const [manualText, setManualText] = useState("");
  const [captionText, setCaptionText] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [transcribing, setTranscribing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [exportingSrt, setExportingSrt] = useState(false);
  const [exportingVtt, setExportingVtt] = useState(false);
  const [detectingFillers, setDetectingFillers] = useState(false);

  useEffect(() => {
    api.transcriptionStatus().then(setStatus);
    api.transcriptions().then(setTranscripts);
  }, []);

  useEffect(() => {
    if (!assetId) return;
    api.transcriptions(assetId).then(setTranscripts);
  }, [assetId]);

  const transcribe = async () => {
    if (!assetId) return;
    try {
      setTranscribing(true);
      setMessage(null);
      const response = await api.transcribeAsset({ asset_id: assetId, language: "pt" });
      setResult(response);
      setManualText(response.text);
      setTranscripts(await api.transcriptions(assetId));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Falha ao transcrever.");
    } finally {
      setTranscribing(false);
    }
  };

  const saveManualTranscript = async () => {
    if (!assetId || !manualText.trim()) {
      setMessage("Selecione um video e cole um texto antes de salvar.");
      return;
    }
    try {
      setSaving(true);
      const transcript = await api.createManualTranscription({ asset_id: assetId, text: manualText, language: "pt" });
      setTranscripts(await api.transcriptions(assetId));
      setResult({ asset_id: transcript.asset_id, transcript_id: transcript.id, path: "manual", text: transcript.text });
      setMessage("Transcricao manual salva no banco.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Falha ao salvar transcricao manual.");
    } finally {
      setSaving(false);
    }
  };

  const exportCaptions = async (format: "srt" | "vtt") => {
    const text = result?.text || manualText;
    if (!text) {
      setMessage("Gere uma transcricao antes de exportar captions.");
      return;
    }
    const setLoader = format === "srt" ? setExportingSrt : setExportingVtt;
    try {
      setLoader(true);
      const selectedAsset = assets.find((asset) => asset.id === (result?.asset_id ?? assetId));
      const response = await api.exportCaptions({
        format,
        segments: [
          {
            start: 0,
            end: Math.max(selectedAsset?.duration_seconds ?? 1, 1),
            text
          }
        ]
      });
      setCaptionText(response.text);
      setMessage(`Caption ${format.toUpperCase()} gerada.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Falha ao gerar caption.");
    } finally {
      setLoader(false);
    }
  };

  const detectFillers = async () => {
    const text = result?.text || manualText;
    if (!text) {
      setMessage("Nenhum texto para analisar.");
      return;
    }
    try {
      setDetectingFillers(true);
      const fillers = await api.captionFillers({ segments: [{ start: 0, end: 1, text }] });
      setMessage(fillers.words.length ? `Vicios detectados: ${fillers.words.join(", ")}` : "Nenhum vicio comum detectado.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Falha ao detectar vícios.");
    } finally {
      setDetectingFillers(false);
    }
  };

  return (
    <section className="view-grid two-column">
      <div className="panel">
        <div className="panel-heading">
          <div>
            <h2>Transcricao local</h2>
            <p>Usa Whisper CLI quando instalado no Windows/container.</p>
          </div>
          <Captions className={status?.available ? "ok-icon" : "danger-icon"} />
        </div>
        <div className="inline-form">
          <select value={assetId} onChange={(event) => setAssetId(event.target.value)}>
            <option value="">Selecione um video</option>
            {assets.map((asset) => (
              <option key={asset.id} value={asset.id}>
                {asset.filename}
              </option>
            ))}
          </select>
          <Button
            variant="primary"
            compact
            loading={transcribing}
            onClick={transcribe}
            label={transcribing ? "Transcrevendo" : "Transcrever"}
          />
          {assetId ? (
            <button
              className="danger-button compact"
              onClick={() => onDeleteAssets([assetId])}
              title="Remover este video da biblioteca"
              type="button"
            >
              <Trash2 size={14} />
              Excluir
            </button>
          ) : null}
        </div>
        <label>
          Texto manual ou revisado
          <textarea
            className="large-textarea"
            value={manualText}
            onChange={(event) => setManualText(event.target.value)}
            placeholder="Cole uma transcricao aqui quando Whisper nao estiver disponivel."
          />
        </label>
        <Button
          compact
          loading={saving}
          icon={<FileText size={16} />}
          label="Salvar texto manual"
          onClick={saveManualTranscript}
        />
        <div className="rule-list">
          <span>{status?.available ? "Whisper disponivel" : "Whisper pendente"}</span>
          <span>Modelo: {status?.model ?? "base"}</span>
          <span>Saida em data/transcripts</span>
        </div>
        <div className="command-actions left">
          <Button
            compact
            loading={exportingSrt}
            icon={<Subtitles size={16} />}
            label="Gerar SRT"
            onClick={() => exportCaptions("srt")}
          />
          <Button
            compact
            loading={exportingVtt}
            icon={<Subtitles size={16} />}
            label="Gerar VTT"
            onClick={() => exportCaptions("vtt")}
          />
          <Button
            compact
            loading={detectingFillers}
            icon={<Captions size={16} />}
            label="Detectar vicios"
            onClick={detectFillers}
          />
        </div>
        {message ? <p className="inline-error">{message}</p> : null}
      </div>
      <aside className="panel">
        <div className="panel-heading">
          <div>
            <h2>Segmentos e Legendas</h2>
            <p>{result?.path ?? `${transcripts.length} transcricao(s) no banco.`}</p>
          </div>
        </div>
        {result?.transcript_id && transcripts.find((t) => t.id === result.transcript_id)?.words?.length ? (
          <div className="tag-list" style={{ marginBottom: "0.5rem" }}>
            <span className="success-pill">
              {transcripts.find((t) => t.id === result.transcript_id)?.words?.length} palavras sincronizadas (word timestamps)
            </span>
          </div>
        ) : null}
        {result?.transcript_id && transcripts.find((t) => t.id === result.transcript_id)?.segments?.length ? (
          <div className="transcript-segments-timeline" style={{ maxHeight: "280px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "0.4rem", marginBottom: "1rem" }}>
            {transcripts.find((t) => t.id === result.transcript_id)?.segments.map((seg, idx) => (
              <div key={idx} style={{ padding: "0.5rem 0.75rem", background: "rgba(255,255,255,0.04)", borderRadius: "6px", fontSize: "0.85rem", borderLeft: "3px solid #51d88a" }}>
                <span style={{ opacity: 0.6, fontSize: "0.75rem", display: "block", marginBottom: "0.2rem" }}>
                  [{Number(seg.start).toFixed(2)}s ➔ {Number(seg.end).toFixed(2)}s]
                </span>
                <strong>{String(seg.text || "")}</strong>
              </div>
            ))}
          </div>
        ) : (
          <pre className="agent-output">{captionText || result?.text || <FileText size={18} />}</pre>
        )}
        <div className="task-list">
          {transcripts.slice(0, 5).map((transcript) => (
            <button
              className="task-row"
              key={transcript.id}
              onClick={() => {
                setResult({
                  asset_id: transcript.asset_id,
                  transcript_id: transcript.id,
                  path: transcript.engine,
                  text: transcript.text
                });
                setManualText(transcript.text);
              }}
              type="button"
            >
              <div>
                <strong>{transcript.engine}</strong>
                <span>{transcript.created_at.slice(0, 19).replace("T", " ")}</span>
              </div>
            </button>
          ))}
        </div>
      </aside>
    </section>
  );
}
