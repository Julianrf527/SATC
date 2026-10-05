import { useCallback, useState, type ReactNode } from "react";
import { AlertCircle, Calendar, Eye, FileText, Upload, Users, XCircle } from "lucide-react";
import { ApiError } from "@shared/lib/api";
import { formatDateTime } from "@shared/lib/format";
import { toastService } from "@shared/lib/toastService";
import { EstadoBadge, Modal } from "@shared/ui";
import type { ProcesoAdapter } from "./adapter";
import FormRevision from "./FormRevision";
import FormSubirVersion from "./FormSubirVersion";
import HistorialRevisiones from "./HistorialRevisiones";
import ListaVersiones from "./ListaVersiones";
import TimelineAuditoria from "./TimelineAuditoria";
import type { CambioProceso, ProcesoDetalle, ResultadoAccion } from "./types";
import { useProcesoRevision } from "./useProcesoRevision";

/** Slot: contenido fijo o función del detalle cargado. */
export type SlotProceso<D> = ReactNode | ((detalle: D) => ReactNode);

export type ProcesoDetalleModalProps<D extends ProcesoDetalle> = {
  adapter: ProcesoAdapter<D>;
  /** Id que entiende el adapter. `null` = cerrado. */
  id: number | null;
  isOpen: boolean;
  onClose: () => void;
  /** Tras revisar / subir versión (el detalle ya se invalidó). */
  onCambio?: (cambio: CambioProceso) => void;
  /** Junto al estado (datos propios del flujo: expediente, tipo...). */
  extraHeader?: SlotProceso<D>;
  /** Botones adicionales del footer (p. ej. abrir la matriz de recursos). */
  extraAcciones?: SlotProceso<D>;
  /** Contenido propio del módulo, antes de versiones/revisiones. */
  children?: SlotProceso<D>;
};

const pintar = <D,>(slot: SlotProceso<D> | undefined, detalle: D): ReactNode =>
  typeof slot === "function" ? (slot as (d: D) => ReactNode)(detalle) : slot;

const mensaje = (error: unknown, fallback: string): string | null => {
  if (!error) return null;
  if (error instanceof ApiError) return error.message || fallback;
  return fallback;
};

const avisar = (resultado: ResultadoAccion, fallback: string) =>
  toastService.showToast({
    id: Date.now(),
    message: typeof resultado.message === "string" && resultado.message ? resultado.message : fallback,
    type: "success",
  });

/**
 * Detalle de un proceso de revisión (genérico para cualquier flujo). Las
 * acciones que ofrece salen SOLO de `acciones_disponibles` y `subida_version`.
 * Lo propio de cada módulo entra por `adapter` y los slots.
 */
export function ProcesoDetalleModal<D extends ProcesoDetalle>({
  adapter,
  id,
  isOpen,
  onClose,
  onCambio,
  extraHeader,
  extraAcciones,
  children,
}: ProcesoDetalleModalProps<D>) {
  const proceso = useProcesoRevision(adapter, isOpen ? id : null, { onCambio });
  const [form, setForm] = useState<"revision" | "version" | null>(null);
  const detalle = proceso.detalle;

  const cerrarForm = () => {
    proceso.revisar.reset();
    proceso.subirVersion.reset();
    setForm(null);
  };

  // Referencias estables para que las secciones memoizadas no se re-dibujen.
  const detalleId = detalle?.id;
  const urlVersion = useCallback(
    (v: Parameters<typeof adapter.urlVersion>[1]) => adapter.urlVersion(detalleId as number, v),
    [adapter, detalleId],
  );
  const urlAdjunto = useCallback(
    (r: Parameters<typeof adapter.urlAdjunto>[1]) => adapter.urlAdjunto(detalleId as number, r),
    [adapter, detalleId],
  );

  const puedeRevisar = (detalle?.acciones_disponibles.length ?? 0) > 0;
  const subida = detalle?.subida_version ?? null;
  const ocupado = proceso.revisar.isPending || proceso.subirVersion.isPending;

  return (
    <>
      <Modal
        isOpen={isOpen}
        onClose={onClose}
        size="4xl"
        icon={<FileText size={20} />}
        title={detalle?.nombre ?? "Proceso de revisión"}
        subtitle={
          detalle
            ? `Versión ${detalle.version_actual} · ${detalle.revisores.length} revisor(es)`
            : undefined
        }
        closeOnEsc={!ocupado}
        footer={
          <>
            {detalle && pintar(extraAcciones, detalle)}
            {subida?.permitida && (
              <button type="button" className="btn btn-sm btn-primary gap-2" onClick={() => setForm("version")}>
                <Upload size={16} />
                Subir versión
              </button>
            )}
            {puedeRevisar && (
              <button type="button" className="btn btn-sm btn-success text-white gap-2" onClick={() => setForm("revision")}>
                <Eye size={16} />
                Revisar
              </button>
            )}
            <button type="button" className="btn btn-sm btn-ghost" onClick={onClose}>
              Cerrar
            </button>
          </>
        }
      >
        {proceso.isPending ? (
          <div className="flex justify-center items-center py-16">
            <span className="loading loading-spinner loading-lg text-success" />
          </div>
        ) : !detalle ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <XCircle className="text-error mb-3" size={40} />
            <p className="text-base-content/70">
              {mensaje(proceso.error, "No se pudo cargar el proceso")}
            </p>
          </div>
        ) : (
          <div className="space-y-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-2 min-w-0">
                {detalle.descripcion && <p className="text-base-content/70">{detalle.descripcion}</p>}
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-base-content/60">
                  <span className="flex items-center gap-1">
                    <Calendar size={14} /> Creado: {formatDateTime(detalle.fecha_creacion)}
                  </span>
                  <span className="flex items-center gap-1">
                    <Users size={14} />
                    {detalle.revisores.map((r) => r.nombre ?? `Revisor ${r.revisor_id}`).join(", ") || "Sin revisores"}
                  </span>
                  {detalle.numero_devoluciones > 0 && (
                    <span className="flex items-center gap-1 text-error font-semibold">
                      <XCircle size={14} />
                      {detalle.numero_devoluciones}/{detalle.max_devoluciones} devoluciones
                    </span>
                  )}
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <EstadoBadge etiqueta={detalle.estado.etiqueta} tono={detalle.estado.tono} size="md" />
                {pintar(extraHeader, detalle)}
              </div>
            </div>

            {subida && !subida.permitida && subida.motivo && (
              <div role="status" className="alert py-2 text-sm">
                <AlertCircle size={16} />
                {subida.motivo}
              </div>
            )}

            {pintar(children, detalle)}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <ListaVersiones
                versiones={detalle.versiones}
                versionActual={detalle.version_actual}
                urlVersion={urlVersion}
              />
              <HistorialRevisiones
                revisiones={detalle.revisiones}
                urlAdjunto={urlAdjunto}
              />
            </div>

            <TimelineAuditoria auditoria={detalle.auditoria} />
          </div>
        )}
      </Modal>

      {detalle && (
        <Modal
          isOpen={form === "revision"}
          onClose={cerrarForm}
          size="xl"
          icon={<Eye size={20} />}
          title="Revisar"
          subtitle={detalle.nombre}
          closeOnEsc={!proceso.revisar.isPending}
          closeOnBackdrop={!proceso.revisar.isPending}
        >
          <FormRevision
            acciones={detalle.acciones_disponibles}
            isPending={proceso.revisar.isPending}
            error={mensaje(proceso.revisar.error, "Error al registrar la revisión")}
            onCancel={cerrarForm}
            onSubmit={(datos) =>
              proceso.revisar.mutate(datos, {
                onSuccess: (res) => {
                  avisar(res, "Revisión registrada");
                  cerrarForm();
                },
              })
            }
          />
        </Modal>
      )}

      {subida && (
        <Modal
          isOpen={form === "version"}
          onClose={cerrarForm}
          size="xl"
          icon={<Upload size={20} />}
          title="Subir nueva versión"
          subtitle={detalle?.nombre}
          closeOnEsc={!proceso.subirVersion.isPending}
          closeOnBackdrop={!proceso.subirVersion.isPending}
        >
          <FormSubirVersion
            regla={subida}
            isPending={proceso.subirVersion.isPending}
            error={mensaje(proceso.subirVersion.error, "Error al subir la versión")}
            onCancel={cerrarForm}
            onSubmit={(datos) =>
              proceso.subirVersion.mutate(datos, {
                onSuccess: (res) => {
                  avisar(res, "Versión subida");
                  cerrarForm();
                },
              })
            }
          />
        </Modal>
      )}
    </>
  );
}

export default ProcesoDetalleModal;
