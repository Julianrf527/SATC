import { ArrowRight, FileSignature, FileText } from "lucide-react";
import { ProcesoDetalleModal } from "@features/proceso-revision";
import { documentoAdapter } from "../../api/documentoAdapter";
import { useInvalidarMisDocumentos } from "../../api/misDocumentos";
import type { ProcesoDocumentoDetalle } from "../../types";
import CargarConceptoFinal from "./CargarConceptoFinal";
import PasosRevision from "./PasosRevision";
import { useIrAlExpediente } from "./useIrAlExpediente";

type Props = {
  /** `proceso_id` (Mis informes / notificación). `null` = cerrado. */
  procesoId: number | null;
  onClose: () => void;
};

/**
 * Proceso de revisión de un documento de concesiones: `ProcesoDetalleModal`
 * con el adapter de /recurso/revision-documentos (como `ProcesoInformeModal`
 * de infraction). Revisar, devolver (con adjunto) y subir versión salen de
 * `acciones_disponibles` / `subida_version` del backend.
 *
 * La versión FINAL firmada no se sube por B (el backend responde 409): en
 * "aprobado para firma" el técnico carga su concepto aquí mismo (C.4) y el
 * abogado ve un aviso que lo lleva a la etapa.
 */
export default function ProcesoDocumentoModal({ procesoId, onClose }: Props) {
  const invalidar = useInvalidarMisDocumentos();
  const { puedeGestionar, puedeIr, ir } = useIrAlExpediente();

  const irALaEtapa = (d: ProcesoDocumentoDetalle) => {
    onClose();
    ir(d);
  };

  return (
    <ProcesoDetalleModal
      adapter={documentoAdapter}
      id={procesoId}
      isOpen={procesoId !== null}
      onClose={onClose}
      onCambio={() => void invalidar()}
      extraHeader={(d) => (
        <span className="badge badge-ghost gap-1" title="Expediente">
          <FileText size={12} />
          {d.expediente_codigo ?? d.expediente_radicado ?? `#${d.expediente_id}`} · {d.etapa_padre_etiqueta ?? d.etapa_etiqueta}
          {!d.activo && " · inactivo"}
        </span>
      )}
      extraAcciones={(d) =>
        puedeIr ? (
          <button type="button" className="btn btn-sm btn-ghost gap-2 mr-auto" onClick={() => irALaEtapa(d)}>
            Ver en el expediente
            <ArrowRight size={14} />
          </button>
        ) : null
      }
    >
      {(d) => (
        <div className="space-y-3">
          <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-base-content/70">
            <span>
              Documento: <span className="font-medium text-base-content">{d.tipo_documento_etiqueta}</span>
            </span>
            {d.encargado_nombre && (
              <span>
                Encargado: <span className="font-medium text-base-content">{d.encargado_nombre}</span>
              </span>
            )}
            <span>
              Paso {d.paso_actual} de {d.total_pasos}
            </span>
          </div>

          {/* Encargado (subida_version ≠ null) con el documento aprobado para firma. */}
          {d.estado.codigo === "aprobado_firma" && d.subida_version !== null && (
            // El técnico no entra a Gestionar: carga su concepto firmado aquí (C.4).
            // Los actos los carga el abogado desde la etapa ("Ir a la etapa").
            d.etapa_tipo === "concepto_tecnico" ? (
              <CargarConceptoFinal conceptoId={d.etapa_ref_id} onCargado={onClose} />
            ) : (
              <div role="status" className="alert alert-success py-2 text-sm">
                <FileSignature size={16} />
                <span className="flex-1">
                  Aprobado para firma. La versión firmada (PDF) se carga desde la etapa con "Cargar versión final", no
                  desde aquí.
                </span>
                {puedeGestionar && (
                  <button type="button" className="btn btn-xs btn-success text-white gap-1" onClick={() => irALaEtapa(d)}>
                    Ir a la etapa
                    <ArrowRight size={12} />
                  </button>
                )}
              </div>
            )
          )}

          <PasosRevision pasos={d.pasos ?? []} />
        </div>
      )}
    </ProcesoDetalleModal>
  );
}
