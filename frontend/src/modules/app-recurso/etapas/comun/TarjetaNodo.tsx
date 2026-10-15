import type { ReactNode } from "react";

type Tono = "success" | "info" | "warning" | "error" | "neutral";

const FONDO_ICONO: Record<Tono, string> = {
  success: "bg-success/10 text-success",
  info: "bg-info/10 text-info",
  warning: "bg-warning/10 text-warning",
  error: "bg-error/10 text-error",
  neutral: "bg-base-200 text-base-content/60",
};

type Props = {
  titulo: string;
  subtitulo?: ReactNode;
  /** Clase de boxicons (como las pestañas). */
  icono: string;
  tono?: Tono;
  /** Badges de estado junto al título (derecha). */
  estado?: ReactNode;
  /** Botones de acción (derecha). */
  acciones?: ReactNode;
  /** Sub-proceso dentro de una etapa: tarjeta más sobria. */
  anidada?: boolean;
  children?: ReactNode;
};

/**
 * Tarjeta de una etapa o sub-proceso, con el mismo marcado que las de
 * infraction (InformeTecnicoDatos / ConceptoData): icono, título, estado y
 * acciones en la cabecera; datos debajo.
 */
export default function TarjetaNodo({ titulo, subtitulo, icono, tono = "success", estado, acciones, anidada, children }: Props) {
  return (
    <div
      className={
        anidada
          ? "border border-base-300 rounded-xl p-4 bg-base-100"
          : "card bg-base-100 shadow-md border border-base-300"
      }
    >
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
