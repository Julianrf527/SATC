import type { ReactNode } from "react";

type Tono = "success" | "info" | "warning" | "neutral";

const FONDO_ICONO: Record<Tono, string> = {
  success: "bg-success/10 text-success",
  info: "bg-info/10 text-info",
  warning: "bg-warning/10 text-warning",
  neutral: "bg-base-200 text-base-content/60",
};

type Props = {
  titulo: string;
  subtitulo?: ReactNode;
  /** Clase de boxicons (como las pestañas). */
  icono: string;
  tono?: Tono;
  /** Badges de estado junto a las acciones (derecha). */
  estado?: ReactNode;
  /** Botones de acción (derecha). */
  acciones?: ReactNode;
  /** Dentro de otra tarjeta (p. ej. la medida preventiva): más sobria. */
  anidada?: boolean;
  children?: ReactNode;
};

/**
 * Tarjeta del acto de una etapa, con el mismo marcado que `TarjetaNodo` de
 * recurso (un módulo no importa otro): icono, título, estado y acciones en
 * la cabecera; datos debajo.
 */
export default function TarjetaActo({ titulo, subtitulo, icono, tono = "info", estado, acciones, anidada, children }: Props) {
  return (
    <div className={anidada ? "border border-base-300 rounded-xl p-4 bg-base-100" : "card bg-base-100 shadow-md border border-base-300"}>
      <div className={anidada ? "" : "card-body"}>
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-3">
            <div className={`${anidada ? "w-9 h-9" : "w-10 h-10"} rounded-lg flex items-center justify-center ${FONDO_ICONO[tono]}`}>
              <i className={`bx ${icono} ${anidada ? "text-lg" : "text-xl"}`}></i>
            </div>
            <div>
              <h3 className={anidada ? "text-base font-bold" : "text-xl font-bold"}>{titulo}</h3>
              {subtitulo && <p className="text-sm text-base-content/60">{subtitulo}</p>}
            </div>
          </div>
          {(estado || acciones) && (
            <div className="flex flex-wrap items-center gap-2">
              {estado}
              {acciones}
            </div>
          )}
        </div>
        {children}
      </div>
    </div>
  );
}
