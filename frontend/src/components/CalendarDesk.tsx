import { CalendarDays, Clock3, PackageCheck } from "lucide-react";
import { useState } from "react";

import { api } from "../api";
import type { PublishTask } from "../types";
import type { ViewKey } from "./AppShell";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";

interface CalendarDeskProps {
  tasks: PublishTask[];
  onNavigate: (view: ViewKey) => void;
}

export function CalendarDesk({ tasks, onNavigate }: CalendarDeskProps) {
  const days = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"];
  const ready = tasks.filter((task) => task.status === "ready");
  const [slots, setSlots] = useState<Array<{ publish_at: string; platform: string }>>([]);
  const [loading, setLoading] = useState(false);

  const buildWeek = async () => {
    try {
      setLoading(true);
      const result = await api.buildCalendar({
        start_at: new Date().toISOString(),
        count: 7,
        interval_minutes: 1440,
        platforms: ["instagram_reels", "tiktok", "youtube_shorts"]
      });
      setSlots(result.slots);
    } catch (err) {
      // Ignora graciosamente falhas de conexão
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="view-grid calendar-layout">
      <Card
        title="Calendario"
        eyebrow="publicacao manual"
        action={<Button compact loading={loading} icon={<PackageCheck size={16} />} label="Criar semana" onClick={buildWeek} />}
      >
        <div className="calendar-grid">
          {days.map((day, index) => (
            <div className="calendar-day" key={day}>
              <strong>{day}</strong>
              <span>{index + 1} slots</span>
              {slots[index] ? (
                <small>{slots[index].platform}</small>
              ) : ready[index] ? (
                <small>{ready[index].platform}</small>
              ) : (
                <small>livre</small>
              )}
            </div>
          ))}
        </div>
      </Card>

      <Card title="Fila de pacotes" eyebrow="sem postagem automatica">
        <div className="action-list">
          {ready.slice(0, 6).map((task) => (
            <button key={task.id} onClick={() => onNavigate("publicacao")} type="button">
              <Clock3 size={18} />
              <span>{task.platform} - pronto para agendar manualmente</span>
            </button>
          ))}
          {ready.length === 0 ? (
            <div className="empty-state">
              <CalendarDays size={22} />
              Gere pacotes aprovados antes de montar a semana.
            </div>
          ) : null}
        </div>
      </Card>
    </section>
  );
}
