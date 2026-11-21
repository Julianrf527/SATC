import { ArrowRight, FileSignature, FileText } from "lucide-react";
import { ProcesoDetalleModal } from "@features/proceso-revision";
import { actoAdapter, etiquetaDocumentoActo, useInvalidarActos, type ProcesoActoDetalle } from "../../api/actos";
import PasosRevision from "./PasosRevision";

type Props = {
  procesoId: number | null;
  onClose: () => void;
  /** Abierto desde Consulta: solo ver (sin revisar ni subir versión). */
  soloLectura?: boolean;
  /**
   * Desde Mis actuaciones (como recurso): "Ver en el expediente" y, aprobado
   * para firma, "Ir a la etapa" en el aviso. Sin esta prop (ya estamos en la
   * etapa) no se muestran.
   */
  onIrAlExpediente?: (d: ProcesoActoDetalle) => void;
};

/**
 * Proceso de revisión de un acto administrativo (como `ProcesoEtapaModal` /
 * `ProcesoDocumentoModal` de recurso): `ProcesoDetalleModal` con el adapter
 * de /revision-actos, datos del documento, aviso de "Cargar versión final" y
 * la cadena de revisión. El backend decide las acciones: el líder de
 * proyecto aprueba para firma o devuelve; el encargado actual sube la corrección.
 */
export default function ProcesoActoModal({ procesoId, onClose, soloLectura = false, onIrAlExpediente }: Props) {
  const invalidar = useInvalidarActos();
  const ir = (d: ProcesoActoDetalle) => {
    onClose();
    onIrAlExpediente?.(d);
  };

  return (
    <ProcesoDetalleModal
      adapter={actoAdapter}
      id={procesoId}
      isOpen={procesoId !== null}
      onClose={onClose}
      soloLectura={soloLectura}
      onCambio={() => invalidar()}
      extraHeader={(d) => (
        <span className="badge badge-ghost gap-1" title="Expediente">
          <FileText size={12} />
          {d.expediente_radicado ?? `#${d.expediente_id}`} · {etiquetaDocumentoActo(d)}
          {!d.activo && " · inactivo"}
        </span>
      )}
      extraAcciones={
        onIrAlExpediente
          ? (d) => (
              <button type="button" className="btn btn-sm btn-ghost gap-2 mr-auto" onClick={() => ir(d)}>
                Ver en el expediente
                <ArrowRight size={14} />
              </button>
            )
          : undefined
      }
    >
      {(d) => (
        <div className="space-y-3">
          <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-base-content/70">
            <span>
              Documento: <span className="font-medium text-base-content">{etiquetaDocumentoActo(d)}</span>
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
          {!soloLectura && d.puede_cargar_version_final && (
            <div role="status" className="alert alert-success py-2 text-sm">
              <FileSignature size={16} />
              <span className="flex-1">
                {onIrAlExpediente
                  ? 'Aprobado para firma. La versión firmada (PDF) se carga desde la etapa con "Cargar versión final", no desde aquí.'
                  : 'Aprobado para firma. Cierre esta ventana y cargue la versión firmada (PDF) con "Cargar versión final".'}
              </span>
              {onIrAlExpediente && (
                <button type="button" className="btn btn-xs btn-success text-white gap-1" onClick={() => ir(d)}>
                  Ir a la etapa
                  <ArrowRight size={12} />
                </button>
              )}
            </div>
          )}
          <PasosRevision pasos={d.pasos ?? []} />
        </div>
      )}
    </ProcesoDetalleModal>
  );
}
