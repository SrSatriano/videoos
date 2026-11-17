import { CheckCircle2, Clock3, FileVideo, PackageCheck } from "lucide-react";

import type { Asset, PublishTask, RenderJob, RenderedVideo } from "../types";

interface MetricStripProps {
  assets: Asset[];
  jobs: RenderJob[];
  renders: RenderedVideo[];
  publishTasks: PublishTask[];
}

export function MetricStrip({ assets, jobs, renders, publishTasks }: MetricStripProps) {
  const processing = jobs.filter((job) => job.status === "processing" || job.status === "queued").length;
  const approved = renders.filter((render) => render.status === "approved").length;
  const ready = publishTasks.filter((task) => task.status === "ready").length;
  const metrics = [
    { label: "Assets", value: assets.length, icon: <FileVideo size={20} /> },
    { label: "Fila ativa", value: processing, icon: <Clock3 size={20} /> },
    { label: "Aprovados", value: approved, icon: <CheckCircle2 size={20} /> },
    { label: "Pacotes", value: ready, icon: <PackageCheck size={20} /> }
  ];

  return (
    <section className="metric-strip" aria-label="Resumo operacional">
      {metrics.map((metric) => (
        <div className="metric" key={metric.label}>
          {metric.icon}
          <span>{metric.label}</span>
          <strong>{metric.value}</strong>
        </div>
      ))}
    </section>
  );
}
