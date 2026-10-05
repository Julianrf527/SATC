import { memo } from "react";
import { Paperclip, Users } from "lucide-react";
import { EstadoBadge } from "@shared/ui";
import { formatDateTime } from "@shared/lib/format";
import type { RevisionProceso } from "./types";
import { abrirArchivo } from "./visual";

type Props = {
  revisiones: RevisionProceso[];
  /** Ruta del adjunto de observaciones (la da el adapter del módulo). */
  urlAdjunto: (revision: RevisionProceso) => string;
};

/** Revisiones realizadas, la más reciente primero (orden del backend). */
export function HistorialRevisiones({ revisiones, urlAdjunto }: Props) {
  return (
    <section className="bg-base-200 rounded-lg p-4">
      <h4 className="font-semibold text-base-content mb-3 flex items-center gap-2">
        <Users size={18} />
        Revisiones ({revisiones.length})
      </h4>
      {revisiones.length === 0 ? (
        <p className="text-sm text-base-content/60 text-center py-4">
          Aún no hay revisiones registradas
        </p>
      ) : (
        <ul className="space-y-3 max-h-72 overflow-y-auto">
          {revisiones.map((revision) => (
            <li key={revision.revision_id} className="bg-base-100 rounded-lg p-3 border border-base-300">
              <div className="flex items-start justify-between gap-2 mb-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <EstadoBadge etiqueta={revision.accion_etiqueta} tono={revision.tono} />
                  {revision.version_revisada !== null && (
                    <span className="text-xs text-base-content/60">
                      Versión {revision.version_revisada}
                    </span>
                  )}
                </div>
                {revision.adjunto && (
                  <button
                    type="button"
                    onClick={() => abrirArchivo(urlAdjunto(revision))}
                    className="btn btn-xs btn-outline btn-error gap-1 shrink-0"
                    title={revision.adjunto.nombre ?? "Observaciones"}
                  >
                    <Paperclip size={12} />
                    Observaciones
                  </button>
                )}
              </div>
              <p className="text-xs text-base-content/60 mb-1">
                {formatDateTime(revision.fecha_revision)}
                <span className="ml-2 font-medium">
                  {revision.revisor_nombre || `Revisor ${revision.revisor_id}`}
                </span>
              </p>
              {revision.comentarios && (
                <p className="text-xs text-base-content/70 bg-base-200 rounded p-2 whitespace-pre-line">
                  {revision.comentarios}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// memo: no se re-dibuja al abrir/cerrar los formularios del modal padre.
export default memo(HistorialRevisiones);
