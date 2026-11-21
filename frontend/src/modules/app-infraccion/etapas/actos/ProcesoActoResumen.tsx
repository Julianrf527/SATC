import { useState } from "react";
import { BellRing, Eye, FileCheck2, Upload } from "lucide-react";
import { EstadoBadge } from "@shared/ui";
import { requiereMiAccion, type ProcesoActoDetalle } from "../../api/actos";
import ProcesoActoModal from "./ProcesoActoModal";

/** Estado del acto en revisión (badge del backend) + "Tu turno". */
export function EstadoProcesoActoBadge({ proceso }: { proceso: ProcesoActoDetalle }) {
  return (
    <>
      <EstadoBadge etiqueta={proceso.estado.etiqueta} tono={proceso.estado.tono} size="md" />
      {requiereMiAccion(proceso) && (
        <EstadoBadge etiqueta="Tu turno" tono="info" icono={<BellRing size={11} />} title="Requiere tu acción" />
      )}
    </>
  );
}

type Props = {
  proceso: ProcesoActoDetalle;
  /** Nombre del documento ("Acto de cierre"...). */
  documento: string;
  /** Pantalla de consulta: el modal del proceso abre en solo lectura. */
  soloLectura?: boolean;
};

/**
 * Bloque "Documento en revisión" del acto (como `ProcesoResumen` de recurso):
 * documento, paso, versión, devoluciones y botón al proceso. Revisar,
 * devolver y subir la corrección se hacen dentro del modal.
 */
export default function ProcesoActoResumen({ proceso, documento, soloLectura = false }: Props) {
  const [abierto, setAbierto] = useState<number | null>(null);
  const puedeSubir = !soloLectura && !!proceso.subida_version?.permitida;
  const puedeRevisar = !soloLectura && proceso.acciones_disponibles.length > 0;

  const etiquetaBoton = puedeSubir ? "Subir versión" : puedeRevisar ? "Revisar documento" : "Ver proceso de revisión";
  const Icono = puedeSubir ? Upload : puedeRevisar ? FileCheck2 : Eye;
  const pendiente = proceso.pasos
    .find((p) => p.estado === "actual")
    ?.permisos.filter((p) => !p.revisado)
    .map((p) => p.etiqueta);

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-base-200/50 rounded-lg border border-base-300">
      <div className="text-sm space-y-0.5">
        <p className="font-medium">
          {documento}
          {proceso.total_pasos > 0 && (
            <span className="text-base-content/60 font-normal">
              {" "}
              · paso {proceso.paso_actual} de {proceso.total_pasos}
            </span>
          )}
        </p>
        <p className="text-xs text-base-content/60">
          Versión {proceso.version_actual}
          {proceso.numero_devoluciones > 0 && ` · ${proceso.numero_devoluciones} devolución(es)`}
          {proceso.estado.codigo === "en_revision" && pendiente && pendiente.length > 0 && ` · pendiente de: ${pendiente.join(", ")}`}
          {proceso.estado.codigo === "pendiente_carga" && " · pendiente de carga del abogado encargado"}
          {proceso.estado.codigo === "rechazado" && " · pendiente de la corrección del abogado encargado"}
        </p>
      </div>
      <button
        type="button"
        className={`btn btn-sm gap-2 ${puedeSubir || puedeRevisar ? "btn-info text-white" : "btn-outline"}`}
        onClick={() => setAbierto(proceso.id)}
      >
        <Icono size={14} />
        {etiquetaBoton}
      </button>
      <ProcesoActoModal procesoId={abierto} onClose={() => setAbierto(null)} soloLectura={soloLectura} />
    </div>
  );
}
