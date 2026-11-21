import { useState } from "react";
import { FileText, CalendarDays } from "lucide-react";
import { openDocumentById } from "@shared/lib/documentViewer";
import { formatDate } from "@shared/lib/format";
import { Modal } from "@shared/ui";
import type { SolicitudInformacion } from "../../types";
import { useEliminarSolicitudInformacionMutation } from "../../api/etapas";
import { detalleError } from "../../api/errors";
import SolicitudInformacionModal from "./SolicitudInformacionModal";

type Props = {
  etapaConceptoId: number;
  expedienteId: number;
  solicitud: SolicitudInformacion | null;
  isEditable: boolean;
  setToast: (t: { id: number; message: string; type: "success" | "error" }) => void;
};

const mensajeError = (err: unknown, fallback: string) =>
  detalleError(err) ?? (err instanceof Error && err.message ? err.message : fallback);

/**
 * Solicitud de información de la etapa 3 (independiente del tipo de
 * acogida). Agregar y editar se hacen en modal (`SolicitudInformacionModal`).
 */
export default function SolicitudInformacionCard({
  etapaConceptoId,
  expedienteId,
  solicitud,
  isEditable,
  setToast,
}: Props) {
  const [modal, setModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const eliminarSolicitud = useEliminarSolicitudInformacionMutation(expedienteId);
  const isDeleting = eliminarSolicitud.isPending;

  const handleDelete = () => {
    if (!solicitud) return;
    eliminarSolicitud.mutate(solicitud.id, {
      onSuccess: () => {
        setToast({ id: Date.now(), message: "Solicitud de información eliminada", type: "success" });
        setShowDeleteConfirm(false);
      },
      onError: (err) =>
        setToast({ id: Date.now(), message: mensajeError(err, "Error al eliminar la solicitud"), type: "error" }),
    });
  };


  return (
    <div className="card bg-base-100 shadow-md border border-base-300">
      <div className="card-body gap-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-info/10 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-info" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <h4 className="font-bold">Solicitud de Información</h4>
              <p className="text-xs text-base-content/60">
                {solicitud ? "Información de la solicitud registrada" : "Se puede agregar en cualquier momento"}
              </p>
            </div>
          </div>
          {isEditable && solicitud && (
            <div className="flex items-center gap-1">
              <button
                className="btn btn-ghost btn-sm gap-2 text-tono-info hover:bg-info/10"
                onClick={() => setModal(true)}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                Editar
              </button>
              <button
                className="btn btn-ghost btn-sm gap-2 text-error hover:bg-error/10"
                onClick={() => setShowDeleteConfirm(true)}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Eliminar
              </button>
            </div>
          )}
          {!solicitud && isEditable && (
            <button
              className="btn btn-info btn-sm text-white gap-2"
              onClick={() => setModal(true)}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              Agregar Solicitud
            </button>
          )}
        </div>

        {/* Vista datos: solicitud y, si la hay, la respuesta del usuario */}
        {solicitud && (
          <div className="space-y-3">
            <BloqueRadicado
              titulo="Solicitud"
              radicado={solicitud.radicado}
              fecha={solicitud.fecha_radicado}
              fileId={solicitud.archivo_solicitud_id}
            />
            {solicitud.radicado_respuesta ? (
              <BloqueRadicado
                titulo="Respuesta del usuario"
                radicado={solicitud.radicado_respuesta}
                fecha={solicitud.fecha_radicado_respuesta}
                fileId={solicitud.archivo_respuesta_id}
              />
            ) : (
              <p className="text-xs text-base-content/60 italic px-1">Sin respuesta del usuario registrada.</p>
            )}
          </div>
        )}

        {modal && (
          <SolicitudInformacionModal
            etapaConceptoId={etapaConceptoId}
            expedienteId={expedienteId}
            solicitud={solicitud}
            setToast={setToast}
            onClose={() => setModal(false)}
          />
        )}

        {/* Modal confirmación eliminar */}
        <Modal
          isOpen={showDeleteConfirm}
          onClose={() => !isDeleting && setShowDeleteConfirm(false)}
          closeOnEsc={!isDeleting}
          title="Eliminar solicitud de información"
          footer={
            <>
              <button className="btn btn-outline" onClick={() => setShowDeleteConfirm(false)} disabled={isDeleting}>
                Cancelar
              </button>
              <button className="btn btn-error text-white gap-2" onClick={handleDelete} disabled={isDeleting}>
                {isDeleting ? (
                  <><span className="loading loading-spinner loading-sm" />Eliminando...</>
                ) : (
                  "Sí, eliminar"
                )}
              </button>
            </>
          }
        >
          <p className="py-4 text-sm text-base-content/80">
            ¿Está seguro de que desea eliminar esta solicitud de información? Esta acción no se puede deshacer.
          </p>
        </Modal>
      </div>
    </div>
  );
}

type BloqueProps = { titulo: string; radicado: string; fecha: string | null; fileId: number | null };

/** Radicado, fecha y documento de la solicitud o de su respuesta. */
function BloqueRadicado({ titulo, radicado, fecha, fileId }: BloqueProps) {
  return (
    <div className="p-4 bg-base-200/40 rounded-xl space-y-3">
      <p className="text-xs font-semibold text-base-content/60 uppercase tracking-wider">{titulo}</p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-info/10 rounded-lg flex items-center justify-center flex-shrink-0">
            <FileText className="text-tono-info" size={18} />
          </div>
          <div>
            <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">Radicado</p>
            <p className="text-sm font-semibold mt-0.5">{radicado}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-info/10 rounded-lg flex items-center justify-center flex-shrink-0">
            <CalendarDays className="text-tono-info" size={18} />
          </div>
          <div>
            <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">Fecha Radicado</p>
            <p className="text-sm font-semibold mt-0.5">{fecha ? formatDate(fecha) : "—"}</p>
          </div>
        </div>
        {fileId && (
          <div className="flex items-end">
            <button type="button" className="btn btn-success btn-sm gap-1 text-white" onClick={() => openDocumentById(fileId)}>
              <FileText size={14} />
              <span className="text-xs">Ver documento</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
