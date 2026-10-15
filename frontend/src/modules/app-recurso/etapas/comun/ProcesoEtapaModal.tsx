import { FileSignature } from "lucide-react";
import { ProcesoDetalleModal } from "@features/proceso-revision";
import { documentoAdapter } from "../../api/documentoAdapter";
import { useInvalidarExpediente } from "../../api/invalidar";
import { useInvalidarMisDocumentos } from "../../api/misDocumentos";
import PasosRevision from "../../layout/mis-informes/PasosRevision";

type Props = {
  expedienteId: number;
  /** `proceso.proceso_id` del nodo. `null` = cerrado. */
  procesoId: number | null;
  onClose: () => void;
};

/**
 * Proceso de revisión de un documento abierto desde su etapa (como el modal
 * del informe en infraction). Revisar, devolver y subir versión salen de
 * `acciones_disponibles` / `subida_version`; al cambiar algo se recargan el
 * árbol de etapas y Mis informes.
 */
export default function ProcesoEtapaModal({ expedienteId, procesoId, onClose }: Props) {
  const invalidarExpediente = useInvalidarExpediente(expedienteId);
  const invalidarMisDocumentos = useInvalidarMisDocumentos();

  return (
    <ProcesoDetalleModal
      adapter={documentoAdapter}
      id={procesoId}
      isOpen={procesoId !== null}
      onClose={onClose}
      onCambio={() => {
        void invalidarExpediente();
        void invalidarMisDocumentos();
      }}
      extraHeader={(d) => <span className="badge badge-ghost">{d.etapa_padre_etiqueta ?? d.etapa_etiqueta}</span>}
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
          {d.estado.codigo === "aprobado_firma" && d.subida_version !== null && (
            <div role="status" className="alert alert-success py-2 text-sm">
              <FileSignature size={16} />
              <span>
                Aprobado para firma. Cierre esta ventana y cargue la versión firmada (PDF) con "Cargar versión final".
              </span>
            </div>
          )}
          <PasosRevision pasos={d.pasos ?? []} />
        </div>
      )}
    </ProcesoDetalleModal>
  );
}
