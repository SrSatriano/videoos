import type { ReactNode } from "react";

interface CardProps {
  title?: string;
  eyebrow?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Card({ title, eyebrow, action, children, className }: CardProps) {
  return (
    <section className={["panel", "ui-card", className ?? ""].filter(Boolean).join(" ")}>
      {title || eyebrow || action ? (
        <div className="panel-heading">
          <div>
            {eyebrow ? <span className="eyebrow">{eyebrow}</span> : null}
            {title ? <h2>{title}</h2> : null}
          </div>
          {action}
        </div>
      ) : null}
      {children}
    </section>
  );
}
