import { Download, FileText, ShieldCheck, X } from "lucide-react";
import { type ChangeEvent, useEffect, useRef, useState } from "react";

import { api } from "../api";
import { toLocalMassloaderPath } from "../massloaderPaths";
import type { DownloadJob, DownloadJobStatus, InstagramStatus } from "../types";
import { Button } from "./ui/Button";

const TERMINAL_STATUSES: DownloadJobStatus[] = [
  "completed",
  "completed_with_errors",
  "failed",
  "canceled",
];

const isActiveStatus = (status: DownloadJobStatus) => !TERMINAL_STATUSES.includes(status);

export function CaptureDesk() {
  const [status, setStatus] = useState<InstagramStatus | null>(null);
  const [source, setSource] = useState("");
  const [limit, setLimit] = useState(100);
  const [offset, setOffset] = useState(0);
  const [destination, setDestination] = useState("");
  const [cookiesFromBrowser, setCookiesFromBrowser] = useState("");
  const [cookiesFilePath, setCookiesFilePath] = useState("");
  const [cookiesFileName, setCookiesFileName] = useState("");
  const [rights, setRights] = useState(false);
  const [importToLibrary, setImportToLibrary] = useState(true);
  const [job, setJob] = useState<DownloadJob | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [cookieUploadLoading, setCookieUploadLoading] = useState(false);
  const cookieInputRef = useRef<HTMLInputElement | null>(null);
  const pollRef = useRef<number | null>(null);

  const stopPolling = () => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  useEffect(() => {
    api.instagramStatus().then(setStatus);
    return () => stopPolling();
  }, []);

  const clearCookieFile = () => {
    setCookiesFilePath("");
    setCookiesFileName("");
    if (cookieInputRef.current) {
      cookieInputRef.current.value = "";
    }
  };

  const uploadCookiesFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      setCookieUploadLoading(true);
      setMessage(null);
      const uploaded = await api.uploadInstagramCookies(file);
      setCookiesFilePath(uploaded.path);
      setCookiesFileName(uploaded.filename);
      setCookiesFromBrowser("");
      setMessage("Arquivo de cookies carregado para o MassLoader.");
    } catch (err) {
      clearCookieFile();
      setMessage(err instanceof Error ? err.message : "Falha ao importar cookies.");
    } finally {
      setCookieUploadLoading(false);
    }
  };

  const capture = async () => {
    try {
      setLoading(true);
      setMessage(null);
      stopPolling();
      const enqueued = await api.captureInstagram({
        source,
        limit,
        offset,
        rights_confirmed: rights,
        import_to_library: importToLibrary,
        cookies_from_browser: cookiesFilePath ? null : cookiesFromBrowser || null,
        cookies_file_path: cookiesFilePath || null,
        destination: destination.trim() || null
      });
      setJob(enqueued);
      if (isActiveStatus(enqueued.status)) {
        pollRef.current = window.setInterval(async () => {
          try {
            const updated = await api.getDownloadJob(enqueued.id);
            setJob(updated);
            if (!isActiveStatus(updated.status)) {
              stopPolling();
              setLoading(false);
            }
          } catch (err) {
            stopPolling();
            setLoading(false);
            setMessage(err instanceof Error ? err.message : "Falha ao consultar o download.");
          }
        }, 1500);
      } else {
        setLoading(false);
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Falha na captura.");
      setLoading(false);
    }
  };

  const browserCookiesSupported = status?.browser_cookie_import_supported ?? true;
  const localTargetPath = job?.target_dir ? toLocalMassloaderPath(job.target_dir) : null;
  const jobActive = job ? isActiveStatus(job.status) : false;

  return (
    <section className="view-grid two-column">
      <div className="panel">
        <div className="panel-heading">
          <div>
            <h2>MassLoader</h2>
            <p>Cole URL de perfil, post/Reel direto, TikTok, YouTube ou uma lista de URLs. Perfis do Instagram baixam via gallery-dl (exigem cookies); URLs diretas usam yt-dlp.</p>
          </div>
          <Download className={status?.configured ? "ok-icon" : "danger-icon"} />
        </div>

        <textarea
          className="large-textarea"
          value={source}
          onChange={(event) => setSource(event.target.value)}
          placeholder={"https://www.instagram.com/perfil/\nhttps://www.instagram.com/reel/...\nhttps://www.tiktok.com/@perfil/video/..."}
        />
        <span style={{ fontSize: "0.8rem", opacity: 0.7, display: "block", marginBottom: "1rem", marginTop: "-0.5rem" }}>
          * Perfis/canais (Instagram, TikTok, YouTube): "Quantidade" = numero de videos e "A partir de" pula os mais recentes.
          Perfil do Instagram exige cookies (arquivo ou navegador padrao). Cookies do navegador so funcionam rodando fora do Docker.
        </span>

        <div className="capture-options-grid">
          <div className="capture-field">
            <span>Quantidade</span>
            <input min={1} max={1000} type="number" value={limit} onChange={(event) => setLimit(Number(event.target.value))} />
          </div>

          <div className="capture-field">
            <span>A partir de</span>
            <input min={0} max={100000} type="number" value={offset} onChange={(event) => setOffset(Number(event.target.value))} />
          </div>

          <div className="capture-field capture-field-wide">
            <span>Pasta de destino (opcional)</span>
            <input
              type="text"
              value={destination}
              onChange={(event) => setDestination(event.target.value)}
              placeholder="ex.: chumai"
            />
            <small>Vazio = pasta automatica com data/hora.</small>
          </div>

          <div className="capture-field capture-field-wide">
            <span>Arquivo de cookies</span>
            <input
              ref={cookieInputRef}
              type="file"
              accept=".txt,.cookies"
              onChange={uploadCookiesFile}
              style={{ display: "none" }}
            />
            <div className="capture-cookie-actions">
              <Button
                compact
                icon={<FileText size={15} />}
                loading={cookieUploadLoading}
                label={cookiesFileName ? "Trocar cookies.txt" : "Selecionar cookies.txt"}
                onClick={() => cookieInputRef.current?.click()}
              />
              {cookiesFileName ? (
                <Button
                  compact
                  icon={<X size={15} />}
                  onClick={clearCookieFile}
                  tooltip="Remover cookies"
                />
              ) : null}
            </div>
            <small className="capture-cookie-name">
              {cookiesFileName || "Sem arquivo de cookies"}
            </small>
          </div>

          {browserCookiesSupported ? (
            <div className="capture-field capture-field-wide">
              <span>Navegador local</span>
              <select
                value={cookiesFromBrowser}
                onChange={(event) => {
                  setCookiesFromBrowser(event.target.value);
                  if (event.target.value) clearCookieFile();
                }}
              >
                <option value="">Sem navegador</option>
                <option value="auto">
                  {status?.default_browser ? `Navegador padrao (${status.default_browser})` : "Navegador padrao (auto)"}
                </option>
                <option value="chrome">Google Chrome</option>
                <option value="edge">Microsoft Edge</option>
                <option value="firefox">Mozilla Firefox</option>
                <option value="brave">Brave Browser</option>
                <option value="opera">Opera</option>
                <option value="vivaldi">Vivaldi</option>
              </select>
            </div>
          ) : null}
        </div>

        <div style={{ marginBottom: "1rem" }}>
          <Button
            variant="primary"
            loading={loading}
            onClick={capture}
            label={loading ? `Baixando... ${job ? `${job.progress}%` : ""}`.trim() : "Baixar em massa"}
          />
        </div>

        <label className="check-row">
          <input checked={rights} onChange={(event) => setRights(event.target.checked)} type="checkbox" />
          <span>Confirmo que tenho direito de baixar e reutilizar estes videos.</span>
        </label>
        <label className="check-row">
          <input checked={importToLibrary} onChange={(event) => setImportToLibrary(event.target.checked)} type="checkbox" />
          <span>Importar automaticamente para a biblioteca depois de baixar.</span>
        </label>
        <div className="rule-list">
          <span>{status?.configured ? `yt-dlp ${status.yt_dlp_version ?? "disponivel"}` : "yt-dlp pendente"}</span>
          <span>{status?.gallery_dl_configured ? `gallery-dl ${status.gallery_dl_version ?? "disponivel"}` : "gallery-dl pendente"}</span>
          <span>Quantidade: {limit}{offset ? ` (a partir de #${offset + 1})` : ""}</span>
          <span>Cookies: {cookiesFileName ? "arquivo" : cookiesFromBrowser === "auto" ? `auto (${status?.default_browser ?? "?"})` : cookiesFromBrowser || "sem cookies"}</span>
          <span>Destino: data/incoming/massloader{destination.trim() ? `/${destination.trim().replace(/\\/g, "/").replace(/^\/+|\/+$/g, "")}` : "/<data-hora>"}</span>
        </div>
        {message ? <p className="inline-error">{message}</p> : null}
      </div>

      <aside className="panel">
        <h2>Download</h2>
        {job ? (
          <div className="resilience-copy">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "0.5rem" }}>
              <strong>
                {jobActive
                  ? job.current_step
                  : job.status === "failed"
                    ? "Falhou"
                    : `${job.downloaded.length} video(s) baixado(s)`}
              </strong>
              <span style={{ fontSize: "0.8rem", opacity: 0.7 }}>{job.progress}%</span>
            </div>

            <div
              style={{
                height: "8px",
                borderRadius: "999px",
                background: "var(--border-color)",
                overflow: "hidden",
                margin: "0.5rem 0 0.75rem"
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${Math.max(2, Math.min(100, job.progress))}%`,
                  background: job.status === "failed" ? "var(--color-danger)" : "var(--color-accent, #51d88a)",
                  transition: "width 0.4s ease"
                }}
              />
            </div>

            <span>{job.downloaded_count} baixado(s){jobActive ? " ate agora" : ""} · {job.imported.length} importado(s).</span>

            {job.target_dir ? (
              <p style={{ wordBreak: "break-all", fontSize: "0.85rem", opacity: 0.8, marginTop: "0.5rem" }}>
                Destino: {job.target_dir}
              </p>
            ) : null}
            {localTargetPath ? (
              <p style={{ wordBreak: "break-all", fontSize: "0.85rem", opacity: 0.8, marginTop: "-0.35rem" }}>
                Local: {localTargetPath}
              </p>
            ) : null}

            {job.error_message && job.status === "failed" ? (
              <p className="inline-error" style={{ fontSize: "0.85rem", marginTop: "0.5rem" }}>{job.error_message}</p>
            ) : null}

            {job.errors.length ? (
              <div style={{ marginTop: "1rem" }}>
                <strong className="inline-error" style={{ fontSize: "0.85rem", display: "block" }}>Mensagens / Alertas do Downloader:</strong>
                <ul className="error-list" style={{ marginTop: "0.25rem", paddingLeft: "1.2rem", fontSize: "0.85rem", color: "var(--color-danger)" }}>
                  {job.errors.map((err, idx) => (
                    <li key={idx} style={{ marginBottom: "0.25rem" }}>{err}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        ) : (
          <div className="empty-state">
            <ShieldCheck size={22} />
            O download roda em segundo plano com progresso ao vivo. Funciona melhor com URLs publicas e conteudo autorizado.
          </div>
        )}
      </aside>
    </section>
  );
}
