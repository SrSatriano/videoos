import {
  Activity,
  AlertCircle,
  Archive,
  Bot,
  CheckCircle2,
  Clock3,
  Cpu,
  Database,
  Film,
  FolderOpen,
  Mic,
  PackageCheck,
  ServerCrash,
  Sparkles
} from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "../api";
import type { AiProvidersStatus, AuditEvent, SystemHealth, SystemSettings } from "../types";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";

type SettingKey = "incoming_dir" | "assets_dir" | "renders_dir" | "publish_packages_dir";

const destinationFields: Array<{ key: SettingKey; label: string }> = [
  { key: "incoming_dir", label: "Downloads do MassLoader" },
  { key: "assets_dir", label: "Biblioteca de videos" },
  { key: "renders_dir", label: "Videos renderizados" },
  { key: "publish_packages_dir", label: "Pacotes de publicacao" }
];

const AUDIT_PAGE_SIZE = 20;

interface SettingsPathFieldProps {
  label: string;
  value: string;
  canPick: boolean;
  onChange: (value: string) => void;
  onPick: () => void;
}

function SettingsPathField({ label, value, canPick, onChange, onPick }: SettingsPathFieldProps) {
  return (
    <label className="settings-path-field">
      <span>{label}</span>
      <div className="path-input-row">
        <input value={value} onChange={(event) => onChange(event.target.value)} />
        {canPick ? (
          <Button
            variant="ghost"
            className="icon-button"
            onClick={onPick}
            tooltip={`Escolher ${label.toLocaleLowerCase("pt-BR")}`}
            icon={<FolderOpen size={16} />}
          />
        ) : null}
      </div>
    </label>
  );
}

interface SystemPanelProps {
  health: SystemHealth | null;
  auditEvents: AuditEvent[];
  onBackup: () => void;
  lastMessage: string | null;
}

export function SystemPanel({ health, auditEvents, onBackup, lastMessage }: SystemPanelProps) {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [settingsError, setSettingsError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [auditLimit, setAuditLimit] = useState(AUDIT_PAGE_SIZE);

  const [aiStatus, setAiStatus] = useState<AiProvidersStatus | null>(null);
  const [googleApiKey, setGoogleApiKey] = useState("");
  const [geminiModel, setGeminiModel] = useState("gemini-2.0-flash");
  const [testingGoogle, setTestingGoogle] = useState(false);
  const [testGoogleResult, setTestGoogleResult] = useState<{ success: boolean; message: string } | null>(null);

  useEffect(() => {
    let active = true;
    api
      .settings()
      .then((result) => {
        if (!active) return;
        setSettings(result);
        if (result.gemini_model) {
          setGeminiModel(result.gemini_model);
        }
        setSettingsError(null);
      })
      .catch((error) => {
        if (!active) return;
        setSettingsError(error instanceof Error ? error.message : "Falha ao carregar caminhos.");
      });

    api
      .getAiStatus()
      .then((status) => {
        if (!active) return;
        setAiStatus(status);
      })
      .catch(() => {});

    return () => {
      active = false;
    };
  }, []);

  const selectFolder = async (key: SettingKey) => {
    const path = await window.videoOS?.pickFolder();
    if (path && settings) setSettings({ ...settings, [key]: path });
  };

  const handleSave = async () => {
    if (!settings) return;
    try {
      setSaving(true);
      setSaveMessage(null);
      const result = await api.updateSettings({
        incoming_dir: settings.incoming_dir,
        assets_dir: settings.assets_dir,
        renders_dir: settings.renders_dir,
        publish_packages_dir: settings.publish_packages_dir,
        google_api_key: googleApiKey.trim() ? googleApiKey.trim() : undefined,
        gemini_model: geminiModel
      });
      setSettings(result);
      setGoogleApiKey("");
      setSaveMessage("Configuracoes e credenciais salvas.");
      const updatedAi = await api.getAiStatus();
      setAiStatus(updatedAi);
    } catch (error) {
      setSaveMessage(`Erro: ${error instanceof Error ? error.message : "Falha ao salvar."}`);
    } finally {
      setSaving(false);
    }
  };

  const handleTestGoogle = async () => {
    try {
      setTestingGoogle(true);
      setTestGoogleResult(null);
      const res = await api.testGoogleApi({
        api_key: googleApiKey.trim() || undefined,
        model: geminiModel
      });
      if (res.available) {
        setTestGoogleResult({
          success: true,
          message: `Conexao estabelecida com sucesso com o Google Gemini (${res.model ?? geminiModel})!`
        });
        const updatedAi = await api.getAiStatus();
        setAiStatus(updatedAi);
      } else {
        setTestGoogleResult({
          success: false,
          message: `Falha na conexao: ${res.error || "A API do Google nao respondeu com sucesso."}`
        });
      }
    } catch (error) {
      setTestGoogleResult({
        success: false,
        message: `Erro ao testar: ${error instanceof Error ? error.message : "Falha na requisicao."}`
      });
    } finally {
      setTestingGoogle(false);
    }
  };

  const handleReset = async () => {
    try {
      setSaving(true);
      setSaveMessage(null);
      const result = await api.resetSettings();
      setSettings(result);
      setSaveMessage("Caminhos restaurados para o padrao.");
    } catch (error) {
      setSaveMessage(`Erro: ${error instanceof Error ? error.message : "Falha ao restaurar."}`);
    } finally {
      setSaving(false);
    }
  };

  const importRoots = health?.import_roots ?? [];
  const outputRoots = health?.allowed_output_roots ?? settings?.allowed_output_roots ?? [];
  const activeQueue = (health?.queue.queued ?? 0) + (health?.queue.processing ?? 0);
  const failedQueue = health?.queue.failed ?? 0;
  const visibleAuditEvents = auditEvents.slice(0, auditLimit);

  return (
    <section className="system-workspace">
      <div className="view-grid system-primary-grid">
        <Card
          title="Integridade local"
          eyebrow="runtime"
          className="system-health-panel"
          action={health?.ffmpeg.available ? <CheckCircle2 className="ok-icon" /> : <ServerCrash className="danger-icon" />}
        >
          <div className="system-status-grid">
            <div className={health ? "system-status-item success" : "system-status-item danger"}>
              <Activity size={17} />
              <span>API</span>
              <strong>{health?.status ?? "offline"}</strong>
            </div>
            <div className={health?.ffmpeg.available ? "system-status-item success" : "system-status-item danger"}>
              <Film size={17} />
              <span>FFmpeg</span>
              <strong>{health?.ffmpeg.available ? "disponivel" : "ausente"}</strong>
            </div>
            <div className={health ? "system-status-item info" : "system-status-item danger"}>
              <Database size={17} />
              <span>SQLite</span>
              <strong>{health?.database.journal_mode?.toUpperCase() ?? "offline"}</strong>
            </div>
            <div className={failedQueue ? "system-status-item danger" : "system-status-item neutral"}>
              <Clock3 size={17} />
              <span>Fila</span>
              <strong>{activeQueue} ativos / {failedQueue} falhos</strong>
            </div>
          </div>

          <div className="system-facts-grid">
            <span>Banco</span>
            <code title={health?.database.path}>{health?.database.path ?? "offline"}</code>
            <span>Timeout DB</span>
            <strong>{health ? `${health.database.busy_timeout_ms / 1000}s` : "offline"}</strong>
            <span>FFprobe</span>
            <strong>{health?.ffmpeg.ffprobe ? "disponivel" : "ausente"}</strong>
            <span>Assets</span>
            <strong>{health?.counts.assets ?? 0}</strong>
            <span>Jobs</span>
            <strong>{health?.counts.jobs ?? 0}</strong>
            <span>Renders</span>
            <strong>{health?.counts.renders ?? 0}</strong>
            <span>Pacotes</span>
            <strong>{health?.counts.publish_tasks ?? 0}</strong>
            {health?.storage ? (
              <>
                <span>Volume data/</span>
                <strong>{(health.storage.total_bytes / (1024 * 1024)).toFixed(1)} MB</strong>
                <span>Assets / Renders</span>
                <strong>
                  {(health.storage.assets_bytes / (1024 * 1024)).toFixed(1)} MB / {(health.storage.renders_bytes / (1024 * 1024)).toFixed(1)} MB
                </strong>
              </>
            ) : null}
          </div>

          <div className="system-roots-grid">
            <div className="roots-list">
              <span>Raizes de importacao</span>
              {importRoots.length ? importRoots.map((root) => <code key={root}>{root}</code>) : <code>offline</code>}
            </div>
            <div className="roots-list">
              <span>Saidas permitidas</span>
              {outputRoots.length ? outputRoots.map((root) => <code key={root}>{root}</code>) : <code>offline</code>}
            </div>
          </div>
        </Card>

        <Card title="Caminhos e destinos" eyebrow="armazenamento" className="system-destinations-panel">
          {settings ? (
            <div className="settings-path-list">
              {destinationFields.map((field) => (
                <SettingsPathField
                  key={field.key}
                  label={field.label}
                  value={settings[field.key]}
                  canPick={Boolean(window.videoOS?.isDesktop)}
                  onChange={(value) => setSettings({ ...settings, [field.key]: value })}
                  onPick={() => selectFolder(field.key)}
                />
              ))}
              <div className="system-action-row" style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
                <Button variant="primary" compact loading={saving} label="Salvar caminhos" onClick={handleSave} />
                <Button variant="secondary" compact disabled={saving} label="Restaurar padrões" onClick={handleReset} />
                {saveMessage ? (
                  <span className={saveMessage.startsWith("Erro") ? "settings-message danger" : "settings-message success"}>
                    {saveMessage}
                  </span>
                ) : null}
              </div>
            </div>
          ) : (
            <div className="empty-state">{settingsError ?? "Carregando caminhos do sistema..."}</div>
          )}
        </Card>
      </div>

      <Card
        title="Inteligência Artificial & Google Ecosystem"
        eyebrow="automação neural"
        className="system-ai-panel"
        action={
          aiStatus?.google.configured ? (
            <span style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "12px", padding: "4px 10px", borderRadius: "6px", background: "rgba(81, 216, 138, 0.15)", color: "var(--green)", fontWeight: 600 }}>
              <Sparkles size={14} /> Google Gemini Conectado
            </span>
          ) : (
            <span style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "12px", padding: "4px 10px", borderRadius: "6px", background: "rgba(255, 255, 255, 0.08)", color: "var(--muted)", fontWeight: 600 }}>
              <Cpu size={14} /> Modo Local (Heurístico)
            </span>
          )
        }
      >
        <div className="system-status-grid" style={{ marginBottom: "1.25rem" }}>
          <div className={aiStatus?.google.configured ? "system-status-item success" : "system-status-item neutral"}>
            <Sparkles size={17} />
            <span>Google Gemini</span>
            <strong>{aiStatus?.google.configured ? "Configurado" : "Sem Chave"}</strong>
          </div>
          <div className={aiStatus?.tts.available ? "system-status-item success" : "system-status-item danger"}>
            <Mic size={17} />
            <span>Edge-TTS Neural</span>
            <strong>{aiStatus?.tts.available ? "Operacional" : "Indisponível"}</strong>
          </div>
          <div className={aiStatus?.whisper.available ? "system-status-item info" : "system-status-item neutral"}>
            <Bot size={17} />
            <span>Whisper ASR</span>
            <strong>{aiStatus?.whisper.available ? "Disponível" : "Indisponível"}</strong>
          </div>
          <div className={aiStatus?.ollama.available ? "system-status-item info" : "system-status-item neutral"}>
            <Cpu size={17} />
            <span>Ollama Local</span>
            <strong>{aiStatus?.ollama.available ? "Online" : "Offline"}</strong>
          </div>
        </div>

        <div style={{ display: "grid", gap: "1rem", background: "rgba(255, 255, 255, 0.02)", padding: "1.25rem", borderRadius: "8px", border: "1px solid var(--line)" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem" }}>
            <label className="settings-path-field">
              <span>Chave de API Google Gemini (AI Studio)</span>
              <div className="path-input-row">
                <input
                  type="password"
                  value={googleApiKey}
                  onChange={(e) => setGoogleApiKey(e.target.value)}
                  placeholder={settings?.google_api_key_configured ? "•••••••• (Chave ativa no servidor - digite para alterar)" : "Cole sua chave do Google Gemini..."}
                />
              </div>
              <small style={{ fontSize: "11px", color: "var(--muted)", marginTop: "4px", display: "block" }}>
                Chave para mineração viral, análise de retenção e roteiros. Obtenha grátis em <a href="https://aistudio.google.com/apikey" target="_blank" rel="noreferrer" style={{ color: "var(--blue)" }}>aistudio.google.com</a>
              </small>
            </label>

            <label className="settings-path-field">
              <span>Modelo Gemini</span>
              <div className="path-input-row">
                <select
                  value={geminiModel}
                  onChange={(e) => setGeminiModel(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    background: "var(--surface-2)",
                    border: "1px solid var(--line)",
                    borderRadius: "6px",
                    color: "var(--text)"
                  }}
                >
                  <option value="gemini-2.0-flash">Gemini 2.0 Flash (Recomendado - Rápido, Multimodal & Grátis)</option>
                  <option value="gemini-2.0-flash-lite">Gemini 2.0 Flash Lite (Baixa latência)</option>
                  <option value="gemini-1.5-pro">Gemini 1.5 Pro (Raciocínio complexo & 2M tokens)</option>
                  <option value="gemini-1.5-flash">Gemini 1.5 Flash (Geração anterior estável)</option>
                </select>
              </div>
              <small style={{ fontSize: "11px", color: "var(--muted)", marginTop: "4px", display: "block" }}>
                O modelo analisa a transcrição e pontua ganchos e momentos de pico de retenção.
              </small>
            </label>
          </div>

          <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap", paddingTop: "0.5rem" }}>
            <Button
              variant="secondary"
              compact
              loading={testingGoogle}
              label="Testar Conexão Google AI"
              onClick={handleTestGoogle}
              icon={<Sparkles size={15} />}
            />
            <Button
              variant="primary"
              compact
              loading={saving}
              label="Salvar Chave e Modelo"
              onClick={handleSave}
            />
            {testGoogleResult && (
              <span
                style={{
                  fontSize: "12.5px",
                  padding: "5px 12px",
                  borderRadius: "6px",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  background: testGoogleResult.success ? "rgba(81, 216, 138, 0.15)" : "rgba(255, 118, 104, 0.15)",
                  color: testGoogleResult.success ? "var(--green)" : "var(--red)"
                }}
              >
                {testGoogleResult.success ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
                {testGoogleResult.message}
              </span>
            )}
          </div>
        </div>
      </Card>

      <div className="view-grid system-secondary-grid">
        <Card
          title="Backup local"
          eyebrow="resiliencia"
          action={<Button variant="primary" compact icon={<Archive size={16} />} label="Criar backup" onClick={onBackup} />}
        >
          <div className="resilience-copy">
            <Database size={22} />
            <p>Snapshot consistente do SQLite e manifesto local dentro da pasta de dados.</p>
            {lastMessage ? <strong>{lastMessage}</strong> : null}
          </div>
        </Card>
        <Card title="Capacidade atual" eyebrow="acervo">
          <div className="capacity-strip">
            <span><Film size={17} /> <strong>{health?.counts.assets ?? 0}</strong> assets</span>
            <span><PackageCheck size={17} /> <strong>{health?.counts.publish_tasks ?? 0}</strong> pacotes</span>
            <span><Activity size={17} /> <strong>{health?.queue.completed ?? 0}</strong> jobs concluidos</span>
          </div>
        </Card>
      </div>

      <Card title="Historico de auditoria" eyebrow="rastreabilidade" className="system-audit-panel">
        <div className="audit-table-wrapper">
          <table className="audit-table">
            <thead>
              <tr>
                <th>Data</th>
                <th>Evento</th>
                <th>Tipo</th>
                <th>Entidade</th>
                <th>Mensagem</th>
              </tr>
            </thead>
            <tbody>
              {auditEvents.length === 0 ? (
                <tr>
                  <td colSpan={5} className="audit-empty">Nenhum evento registrado.</td>
                </tr>
              ) : (
                visibleAuditEvents.map((event) => (
                  <tr key={event.id}>
                    <td data-label="Data">{new Date(event.created_at).toLocaleString("pt-BR")}</td>
                    <td data-label="Evento"><span className="audit-event-badge">{event.event_type}</span></td>
                    <td data-label="Tipo">{event.entity_type}</td>
                    <td data-label="Entidade"><code>{event.entity_id.slice(0, 8)}</code></td>
                    <td data-label="Mensagem">{event.message}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        {auditEvents.length > AUDIT_PAGE_SIZE ? (
          <div className="audit-table-footer">
            <span>
              Exibindo {Math.min(auditLimit, auditEvents.length)} de {auditEvents.length} eventos
            </span>
            <Button
              variant="ghost"
              compact
              label={auditLimit < auditEvents.length ? "Mostrar mais" : "Mostrar menos"}
              onClick={() => setAuditLimit((current) => current < auditEvents.length ? current + AUDIT_PAGE_SIZE : AUDIT_PAGE_SIZE)}
            />
          </div>
        ) : null}
      </Card>
    </section>
  );
}
