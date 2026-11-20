import { FileText } from "lucide-react";
import { ProcesoDetalleModal, type SlotProceso } from "@features/proceso-revision";
import { informeAdapter, type ProcesoInformeDetalle } from "../api/informeAdapter";
import { useInvalidarInformes } from "../api/informes";
import CargarVersionFinal from "./CargarVersionFinal";

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
 * backend por usuario. No hay aprobación directa: con el informe "Aprobado
 * para firma" el técnico carga aquí la versión firmada (y la matriz de
 * recursos en VISITA); /versiones responde 409 en ese estado.
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
      {(d) => (
        <>
          {d.profesional_nombre && (
            <p className="text-sm text-base-content/60">
              Técnico asignado: <span className="font-medium text-base-content">{d.profesional_nombre}</span>
            </p>
          )}
          {/* subida_version ≠ null: soy el técnico asignado. */}
          {d.activo && d.estado.codigo === "aprobado_firma" && d.subida_version !== null && (
            <CargarVersionFinal
              procesoId={d.id}
              conMatriz={(d.tipo_informe ?? "").toUpperCase() === "VISITA"}
              onCargado={onClose}
            />
          )}
        </>
      )}
    </ProcesoDetalleModal>
  );
}
