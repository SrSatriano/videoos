import type { ButtonHTMLAttributes, ReactNode } from "react";

import { Tooltip } from "./Tooltip";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: ReactNode;
  label?: string;
  variant?: ButtonVariant;
  compact?: boolean;
  tooltip?: string;
  loading?: boolean;
}

export function Button({
  icon,
  label,
  variant = "secondary",
  compact = false,
  tooltip,
  className,
  loading = false,
  disabled,
  ...props
}: ButtonProps) {
  const button = (
    <button
      className={[
        variant === "primary" ? "primary-button" : variant === "ghost" ? "ghost-button" : "secondary-button",
        variant === "danger" ? "danger-button" : "",
        compact ? "compact" : "",
        loading ? "loading" : "",
        className ?? ""
      ]
        .filter(Boolean)
        .join(" ")}
      disabled={disabled || loading}
      aria-busy={loading ? "true" : undefined}
      aria-label={props["aria-label"] || (!label ? tooltip : undefined)}
      type="button"
      {...props}
    >
      {loading ? (
        <svg className="animate-spin button-loader" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 14, height: 14 }}>
          <path d="M21 12a9 9 0 1 1-6.219-8.56" />
        </svg>
      ) : (
        icon
      )}
      {label && <span>{label}</span>}
    </button>
  );

  return tooltip ? <Tooltip label={tooltip}>{button}</Tooltip> : button;
}
