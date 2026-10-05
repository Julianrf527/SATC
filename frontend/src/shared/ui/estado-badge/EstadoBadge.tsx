import type { ReactNode } from "react";

export type EstadoTono = "info" | "success" | "warning" | "error" | "neutral";

/** Forma que deben producir los mapas estado→badge de cada módulo. */
export type EstadoVisual = {
  etiqueta: ReactNode;
  tono: EstadoTono;
  icono?: ReactNode;
};

export type EstadoBadgeProps = EstadoVisual & {
  size?: "sm" | "md";
  /** Tooltip nativo (p. ej. detalle del estado). */
  title?: string;
  className?: string;
};

// Clases literales completas: Tailwind solo genera lo que encuentra escrito.
const TONO_CLASS: Record<EstadoTono, string> = {
  // text-tono-*: ver app/index.css (oscurece el tono en el tema claro).
  info: "text-tono-info bg-info/10",
  success: "text-tono-success bg-success/10",
  warning: "text-tono-warning bg-warning/10",
  error: "text-tono-error bg-error/10",
  neutral: "text-base-content/70 bg-base-200",
};

const SIZE_CLASS = {
  sm: "text-xs px-2 py-0.5 gap-1",
  md: "text-sm px-2.5 py-1 gap-1.5",
} as const;

/**
 * Badge de estado genérico. NO conoce estados de negocio: cada módulo traduce
 * su estado a `{ etiqueta, tono, icono? }` con un mapa propio, p. ej.:
 *
 *   const ESTADO_INFORME: Record<EstadoInforme, EstadoVisual> = {
 *     aceptado: { etiqueta: "Aceptado", tono: "success", icono: <CheckCircle size={12} /> },
 *     ...
 *   };
 *   <EstadoBadge {...ESTADO_INFORME[informe.estado]} />
 */
export function EstadoBadge({
  etiqueta,
  tono,
  icono,
  size = "sm",
  title,
  className = "",
}: EstadoBadgeProps) {
  return (
    <span
      title={title}
      className={`inline-flex items-center font-semibold rounded-full whitespace-nowrap ${SIZE_CLASS[size]} ${TONO_CLASS[tono]} ${className}`}
    >
      {icono}
      {etiqueta}
    </span>
  );
}

export default EstadoBadge;
