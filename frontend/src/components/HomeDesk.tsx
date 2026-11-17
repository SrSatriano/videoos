import {
  Bot,
  Captions,
  Clapperboard,
  Download,
  FileVideo,
  FolderOpen,
  Gauge,
  PackageCheck,
  Sparkles
} from "lucide-react";

import type { Asset, PublishTask, RenderJob, RenderedVideo, SystemHealth } from "../types";
import type { ViewKey } from "./AppShell";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";

interface HomeDeskProps {
  assets: Asset[];
  jobs: RenderJob[];
  renders: RenderedVideo[];
  publishTasks: PublishTask[];
  health: SystemHealth | null;
  onNavigate: (view: ViewKey) => void;
  onImport: () => void;
  onProcessNext: () => void;
}

export function HomeDesk({ assets, jobs, renders, health, onNavigate, onImport, onProcessNext }: HomeDeskProps) {
  const queued = jobs.filter((job) => job.status === "queued").length;
  const failed = jobs.filter((job) => job.status === "failed").length;
  const pendingReview = renders.filter((render) => render.status === "pending_review").length;
  const nextJobs = jobs.slice(0, 5);

  return (
    <section className="home-desk">
      <div className="production-overview">
        <div className="production-heading">
          <span className="eyebrow">
            <Gauge size={15} /> Operacao local
          </span>
          <h2>Producao de hoje</h2>
          <p>
            {assets.length} videos disponiveis, {queued} na fila e {pendingReview} aguardando revisao.
          </p>
        </div>
        <div className="production-actions">
          <Button icon={<FileVideo size={17} />} label="Importar" onClick={onImport} variant="primary" />
          <Button icon={<Download size={17} />} label="MassLoader" onClick={() => onNavigate("captura")} />
          <Button icon={<Captions size={17} />} label="Transcrever" onClick={() => onNavigate("transcricao")} />
          <Button icon={<Sparkles size={17} />} label="IA Clips" onClick={() => onNavigate("clips")} />
        </div>
      </div>

      <section className="view-grid home-layout">
        <Card
          title="Proximas acoes"
          eyebrow="pipeline"
          action={<Button compact icon={<Clapperboard size={16} />} label="Processar 1" onClick={onProcessNext} />}
        >
          <div className="action-list">
            <button onClick={() => onNavigate("captura")} type="button">
              <Download size={18} />
              <span>Baixar videos publicos/autorizados no MassLoader</span>
            </button>
            <button onClick={() => onNavigate("clips")} type="button">
              <Sparkles size={18} />
              <span>Gerar cortes sugeridos a partir de transcricao</span>
            </button>
            <button onClick={() => onNavigate("marca")} type="button">
              <Bot size={18} />
              <span>Ajustar Brand Kit, CTA e estilo de legenda</span>
            </button>
            <button onClick={() => onNavigate("sistema")} type="button">
              <FolderOpen size={18} />
              <span>Configurar destinos de pastas locais de salvamento</span>
            </button>
            <button onClick={() => onNavigate("calendario")} type="button">
              <PackageCheck size={18} />
              <span>Planejar pacotes por plataforma na semana</span>
            </button>
          </div>
        </Card>

        <div className="home-side-stack">
          <Card title="Fila de hoje" eyebrow="render">
            <div className="job-table compact-table">
              {nextJobs.map((job) => (
                <div className="mini-job-row" key={job.id}>
                  <div>
                    <strong>{job.asset_filename ?? job.asset_id}</strong>
                    <span>{job.current_step}</span>
                  </div>
                  <span>{job.progress}%</span>
                </div>
              ))}
              {nextJobs.length === 0 ? <div className="empty-state">Nenhum job pendente agora.</div> : null}
            </div>
          </Card>

          <Card
            title="Saude local"
            eyebrow="sistema"
            action={<Button compact label="Configurar" onClick={() => onNavigate("sistema")} />}
          >
            <div className="health-grid">
              <span>API</span>
              <strong>{health ? "online" : "offline"}</strong>
              <span>FFmpeg</span>
              <strong>{health?.ffmpeg.available ? "disponivel" : "pendente"}</strong>
              <span>SQLite</span>
              <strong>{health?.database.journal_mode ?? "--"}</strong>
              <span>Falhas</span>
              <strong>{failed}</strong>
            </div>
          </Card>
        </div>
      </section>
    </section>
  );
}
