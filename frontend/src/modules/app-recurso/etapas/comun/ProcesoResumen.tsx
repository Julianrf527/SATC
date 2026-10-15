import { useState } from "react";
import { BellRing, Eye, FileCheck2, Upload } from "lucide-react";
import { EstadoBadge } from "@shared/ui";
import type { ResumenProceso } from "../../types";
import ProcesoEtapaModal from "./ProcesoEtapaModal";

type Props = {
  expedienteId: number;
  proceso: ResumenProceso | null;
  /** El backend manda `subir_version` / `revisar` en el nodo. */
  puedeSubir: boolean;
  puedeRevisar: boolean;
};

/** Estado del documento en revisión (badge del backend) + botón para abrir su proceso. */
export function EstadoProcesoBadge({ proceso }: { proceso: ResumenProceso | null }) {
  if (!proceso?.estado_proceso) return null;
  return (
    <>
      <EstadoBadge etiqueta={proceso.estado_proceso.etiqueta} tono={proceso.estado_proceso.tono} size="md" />
      {proceso.requiere_mi_accion && (
        <EstadoBadge etiqueta="Tu turno" tono="info" icono={<BellRing size={11} />} title="Requiere tu acción" />
      )}
    </>
  );
}

/**
 * Bloque "Documento en revisión" de un nodo: tipo de documento, paso,
 * pendientes y botón al proceso (subir versión / revisar se hacen dentro del
 * modal, como en Mis informes).
 */
export default function ProcesoResumen({ expedienteId, proceso, puedeSubir, puedeRevisar }: Props) {
  const [abierto, setAbierto] = useState<number | null>(null);
  if (!proceso?.proceso_id) return null;

  const etiquetaBoton = puedeSubir ? "Subir versión" : puedeRevisar ? "Revisar documento" : "Ver proceso de revisión";
  const Icono = puedeSubir ? Upload : puedeRevisar ? FileCheck2 : Eye;

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-base-200/50 rounded-lg border border-base-300">
      <div className="text-sm space-y-0.5">
        <p className="font-medium">
          {proceso.tipo_documento_etiqueta ?? "Documento"}
          {proceso.paso_actual !== null && proceso.total_pasos > 0 && (
            <span className="text-base-content/60 font-normal">
              {" "}
              · paso {proceso.paso_actual} de {proceso.total_pasos}
            </span>
          )}
        </p>
        <p className="text-xs text-base-content/60">
          Versión {proceso.version_actual}
          {proceso.numero_devoluciones > 0 && ` · ${proceso.numero_devoluciones} devolución(es)`}
          {proceso.permisos_pendientes.length > 0 &&
            ` · pendiente de: ${proceso.permisos_pendientes.map((p) => p.etiqueta).join(", ")}`}
        </p>
      </div>
      <button
        type="button"
        className={`btn btn-sm gap-2 ${puedeSubir || puedeRevisar ? "btn-info text-white" : "btn-outline"}`}
        onClick={() => setAbierto(proceso.proceso_id)}
      >
        <Icono size={14} />
        {etiquetaBoton}
      </button>
      <ProcesoEtapaModal expedienteId={expedienteId} procesoId={abierto} onClose={() => setAbierto(null)} />
    </div>
  );
}
