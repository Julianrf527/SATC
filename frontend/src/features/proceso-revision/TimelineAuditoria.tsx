import { memo } from "react";
import { Clock } from "lucide-react";
import { EstadoBadge } from "@shared/ui";
import { formatDateTime } from "@shared/lib/format";
import type { AuditoriaProceso, TonoProceso } from "./types";

type Props = {
  auditoria: AuditoriaProceso[];
};

// Clases literales completas (Tailwind solo genera lo que encuentra escrito).
const PUNTO_TONO: Record<TonoProceso, string> = {
  info: "bg-info",
  success: "bg-success",
  warning: "bg-warning",
  error: "bg-error",
  neutral: "bg-base-content/40",
};

/**
 * Historial cronológico del proceso. Etiqueta y tono de cada evento los
 * define el flujo en el backend (`accion_etiqueta`, `tono`): la UI no
 * traduce códigos de auditoría.
 */
export function TimelineAuditoria({ auditoria }: Props) {
  if (auditoria.length === 0) return null;
  return (
    <section className="bg-base-200 rounded-lg p-4">
      <h4 className="font-semibold text-base-content mb-3 flex items-center gap-2">
        <Clock size={18} />
        Historial
      </h4>
      <ol className="relative border-s border-base-300 ms-2 space-y-3 max-h-64 overflow-y-auto pe-2">
        {auditoria.map((evento) => (
          <li key={evento.auditoria_id} className="ms-4">
            <span
              className={`absolute -start-1.5 mt-1.5 w-3 h-3 rounded-full border-2 border-base-100 ${PUNTO_TONO[evento.tono]}`}
            />
            <EstadoBadge etiqueta={evento.accion_etiqueta} tono={evento.tono} />
            <p className="text-xs text-base-content/60">{formatDateTime(evento.fecha_accion)}</p>
            {evento.descripcion && (
              <p className="text-xs text-base-content/70">{evento.descripcion}</p>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}

// memo: no se re-dibuja al abrir/cerrar los formularios del modal padre.
export default memo(TimelineAuditoria);
