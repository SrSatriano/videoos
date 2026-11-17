import { Gauge, ListVideo, MapPin, PlaySquare, Scissors, Tags, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { api } from "../api";
import type { Asset, AssetProxy, ExportPreset, SceneMarker } from "../types";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";

interface EditorToolsDeskProps {
  assets: Asset[];
  selectedAssetIds: string[];
  onDeleteAssets: (assetIds: string[]) => void;
}

function formatSeconds(seconds: number | null | undefined): string {
  if (seconds == null) return "--";
  const minutes = Math.floor(seconds / 60);
  const remaining = Math.floor(seconds % 60).toString().padStart(2, "0");
  const fraction = Math.round((seconds % 1) * 10);
  return `${minutes}:${remaining}.${fraction}`;
}

function formatSize(bytes: number): string {
  if (!bytes) return "--";
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function EditorToolsDesk({ assets, selectedAssetIds, onDeleteAssets }: EditorToolsDeskProps) {
  const initialAssetId = selectedAssetIds[0] ?? assets[0]?.id ?? "";
  const [assetId, setAssetId] = useState(initialAssetId);
  const [proxies, setProxies] = useState<AssetProxy[]>([]);
  const [markers, setMarkers] = useState<SceneMarker[]>([]);
  const [exportPresets, setExportPresets] = useState<ExportPreset[]>([]);
  const [threshold, setThreshold] = useState(0.35);
  const [markerTime, setMarkerTime] = useState(0);
  const [markerLabel, setMarkerLabel] = useState("Hook forte");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const selectedAsset = useMemo(() => assets.find((asset) => asset.id === assetId) ?? null, [assets, assetId]);

  useEffect(() => {
    api.exportPresets().then(setExportPresets).catch((err) => setMessage(err instanceof Error ? err.message : "Falha ao carregar presets."));
  }, []);

  useEffect(() => {
    if (!assetId && initialAssetId) setAssetId(initialAssetId);
  }, [assetId, initialAssetId]);

  const refreshTools = async (targetAssetId = assetId) => {
    if (!targetAssetId) return;
    const [proxyResult, markerResult] = await Promise.allSettled([
      api.assetProxies(targetAssetId),
      api.sceneMarkers(targetAssetId)
    ]);
    if (proxyResult.status === "fulfilled") setProxies(proxyResult.value);
    if (markerResult.status === "fulfilled") setMarkers(markerResult.value);
  };

  useEffect(() => {
    refreshTools();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assetId]);

  const runProxy = async () => {
    if (!assetId) return;
    setBusy("proxy");
    try {
      const proxy = await api.generateAssetProxy(assetId);
      setMessage(`Proxy gerado: ${proxy.width ?? "--"}x${proxy.height ?? "--"} - ${formatSize(proxy.size_bytes)}`);
      await refreshTools(assetId);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Falha ao gerar proxy.");
    } finally {
      setBusy(null);
    }
  };

  const runSceneDetect = async () => {
    if (!assetId) return;
    setBusy("scene");
    try {
      const result = await api.detectScenes(assetId, { threshold, limit: 120 });
      setMessage(`${result.count} marcador(es) de cena criado(s).`);
      await refreshTools(assetId);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Falha ao detectar cenas.");
    } finally {
      setBusy(null);
    }
  };

  const saveMarker = async () => {
    if (!assetId) return;
    setBusy("marker");
    try {
      await api.createSceneMarker(assetId, {
        time_seconds: markerTime,
        duration_seconds: null,
        label: markerLabel,
        color: "#51d88a",
        marker_type: "hook",
        notes: "Criado no Editor Tools."
      });
      setMessage("Marcador manual salvo.");
      await refreshTools(assetId);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Falha ao salvar marcador.");
    } finally {
      setBusy(null);
    }
  };

  const removeMarker = async (markerId: string) => {
    await api.deleteSceneMarker(markerId);
    await refreshTools(assetId);
  };

  return (
    <section className="view-grid editor-tools-layout">
      <Card title="Ferramentas de editor" eyebrow="inspirado em Kdenlive, Shotcut e LosslessCut">
        <label>
          Asset ativo
          <select value={assetId} onChange={(event) => setAssetId(event.target.value)}>
            {assets.map((asset) => (
              <option key={asset.id} value={asset.id}>
                {asset.filename}
              </option>
            ))}
          </select>
        </label>
        {selectedAsset ? (
          <div className="asset-picker-row">
            <div className="thumb-frame">
              {selectedAsset.thumbnail_url ? <img src={selectedAsset.thumbnail_url} alt="" /> : <ListVideo size={22} />}
            </div>
            <div className="asset-picker-meta">
              <strong>{selectedAsset.filename}</strong>
              <span>
                {selectedAsset.orientation} - {formatSeconds(selectedAsset.duration_seconds)} -{" "}
                {selectedAsset.width && selectedAsset.height ? `${selectedAsset.width}x${selectedAsset.height}` : "metadata pendente"}
              </span>
            </div>
            <button
              className="danger-button compact"
              onClick={() => onDeleteAssets([selectedAsset.id])}
              title="Remover este video da biblioteca"
              type="button"
            >
              <Trash2 size={14} />
              Excluir
            </button>
          </div>
        ) : (
          <div className="empty-state">Importe um video para usar as ferramentas.</div>
        )}
        {message ? <p className="inline-error">{message}</p> : null}
      </Card>

      <Card title="Proxy / preview leve" eyebrow="playback rapido">
        <div className="proxy-box">
          <Gauge size={24} />
          <div>
            <strong>Gerar proxy 720p</strong>
            <p>Cria uma copia H.264 leve para revisar cortes, cenas e legendas sem travar a maquina.</p>
          </div>
        </div>
        <Button
          icon={<PlaySquare size={16} />}
          label={busy === "proxy" ? "Gerando..." : "Gerar proxy"}
          onClick={runProxy}
          variant="primary"
          disabled={!assetId || busy !== null}
        />
        <div className="template-list preset-list compact-list">
          {proxies.map((proxy) => (
            <article className="template-row preset-row" key={proxy.id}>
              <Gauge size={18} />
              <span>
                <strong>{proxy.width ?? "--"}x{proxy.height ?? "--"} - {proxy.status}</strong>
                <small>{formatSize(proxy.size_bytes)}</small>
              </span>
              {proxy.media_url ? (
                <a className="secondary-button compact" href={proxy.media_url} download>
                  Baixar
                </a>
              ) : null}
            </article>
          ))}
        </div>
      </Card>

      <Card title="Deteccao de cenas e marcadores" eyebrow="timeline assistida">
        <label>
          Sensibilidade de corte
          <input
            max={0.95}
            min={0.05}
            step={0.05}
            type="range"
            value={threshold}
            onChange={(event) => setThreshold(Number(event.target.value))}
          />
        </label>
        <div className="range-readout">Threshold {threshold.toFixed(2)}</div>
        <div className="command-actions left">
          <Button
            compact
            icon={<Scissors size={16} />}
            label={busy === "scene" ? "Detectando..." : "Detectar cenas"}
            onClick={runSceneDetect}
            disabled={!assetId || busy !== null}
          />
        </div>

        <div className="marker-form">
          <label>
            Tempo
            <input min={0} step={0.1} type="number" value={markerTime} onChange={(event) => setMarkerTime(Number(event.target.value))} />
          </label>
          <label>
            Rotulo
            <input value={markerLabel} onChange={(event) => setMarkerLabel(event.target.value)} />
          </label>
          <Button compact icon={<MapPin size={16} />} label="Salvar marcador" onClick={saveMarker} disabled={!assetId || busy !== null} />
        </div>

        <div className="timeline-markers">
          {markers.map((marker) => (
            <article className="marker-row" key={marker.id}>
              <span className="marker-color" style={{ background: marker.color }} />
              <div>
                <strong>{formatSeconds(marker.time_seconds)} - {marker.label}</strong>
                <small>{marker.marker_type} - {marker.source}</small>
              </div>
              <button className="icon-button danger" onClick={() => removeMarker(marker.id)} title="Excluir marcador" type="button">
                <Trash2 size={15} />
              </button>
            </article>
          ))}
          {markers.length === 0 ? <div className="empty-state">Nenhum marcador salvo para este asset.</div> : null}
        </div>
      </Card>

      <Card title="Presets de exportacao" eyebrow="perfil de entrega">
        <div className="preset-grid">
          {exportPresets.map((preset) => (
            <article className="preset-card" key={preset.id}>
              <Tags size={18} />
              <div>
                <strong>{preset.name}</strong>
                <span>{preset.description}</span>
              </div>
              <small>
                {preset.width}x{preset.height} - CRF {preset.crf} - {preset.preset}
              </small>
            </article>
          ))}
        </div>
      </Card>
    </section>
  );
}
