import { AlertTriangle, CheckCircle2, CircleDashed, Loader2, XCircle } from "lucide-react";
import type { ReactNode } from "react";

const statusMap: Record<string, { label: string; tone: string; icon: ReactNode }> = {
  queued: { label: "Na fila", tone: "neutral", icon: <CircleDashed size={14} /> },
  processing: { label: "Processando", tone: "info", icon: <Loader2 size={14} /> },
  canceling: { label: "Cancelando", tone: "danger", icon: <Loader2 size={14} /> },
  pausing: { label: "Pausando", tone: "info", icon: <Loader2 size={14} /> },
  paused: { label: "Pausado", tone: "muted", icon: <CircleDashed size={14} /> },
  completed: { label: "Concluido", tone: "success", icon: <CheckCircle2 size={14} /> },
  failed: { label: "Falhou", tone: "danger", icon: <AlertTriangle size={14} /> },
  canceled: { label: "Cancelado", tone: "muted", icon: <XCircle size={14} /> },
  approved: { label: "Aprovado", tone: "success", icon: <CheckCircle2 size={14} /> },
  rejected: { label: "Reprovado", tone: "danger", icon: <XCircle size={14} /> },
  pending_review: { label: "Revisar", tone: "info", icon: <CircleDashed size={14} /> },
  ready: { label: "Pronto", tone: "success", icon: <CheckCircle2 size={14} /> },
  posted: { label: "Publicado", tone: "success", icon: <CheckCircle2 size={14} /> },
  archived: { label: "Arquivado", tone: "muted", icon: <CircleDashed size={14} /> }
};

export function StatusPill({ status }: { status: string }) {
  const item = statusMap[status] ?? { label: status, tone: "neutral", icon: <CircleDashed size={14} /> };
  return (
    <span className={`status-pill ${item.tone}`} role="status">
      {item.icon}
      {item.label}
    </span>
  );
}
