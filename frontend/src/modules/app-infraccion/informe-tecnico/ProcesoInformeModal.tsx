import { FileText } from "lucide-react";
import { ProcesoDetalleModal, type SlotProceso } from "@features/proceso-revision";
import { informeAdapter, type ProcesoInformeDetalle } from "../api/informeAdapter";
import { useInvalidarInformes } from "../api/informes";

type Props = {
  /** `proceso_id` del informe (viene en los listados y en la etapa). */
  procesoId: number | null;
  onClose: () => void;
  /** Botones propios de la pantalla (p. ej. abrir la matriz de recursos). */
  extraAcciones?: SlotProceso<ProcesoInformeDetalle>;
};

/**
 * Proceso de revisión de un informe técnico: `ProcesoDetalleModal` con el
 * adapter de /revision-informes y los datos del expediente en la cabecera.
 * Las acciones (revisar, aprobar para firma, subir versión) las decide el
 * backend por usuario.
 */
export default function ProcesoInformeModal({ procesoId, onClose, extraAcciones }: Props) {
  const invalidar = useInvalidarInformes();
  return (
    <ProcesoDetalleModal
      adapter={informeAdapter}
      id={procesoId}
      isOpen={procesoId !== null}
      onClose={onClose}
      onCambio={() => invalidar()}
      extraAcciones={extraAcciones}
      extraHeader={(d) => (
        <span className="badge badge-ghost gap-1" title="Expediente">
          <FileText size={12} />
          {d.expediente_radicado ?? `#${d.expediente_id}`} · {d.tipo_informe ?? "Informe"}
          {!d.activo && " · archivado"}
        </span>
      )}
    >
      {(d) =>
        d.profesional_nombre ? (
          <p className="text-sm text-base-content/60">
            Profesional asignado: <span className="font-medium text-base-content">{d.profesional_nombre}</span>
          </p>
        ) : null
      }
    </ProcesoDetalleModal>
  );
}
