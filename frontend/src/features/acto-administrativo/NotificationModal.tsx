import { Modal } from "@shared/ui";
import type {
  TipoNotificacion,
  InvolucradoNotificacion,
} from "@shared/types/sancionatorio";
import type { Involucrado } from "@shared/types/involucrado";
import type { NotificacionFormData } from "./actoAdminConfig";
import { useNotificacionForm } from "./useNotificacionForm";
import NotificacionCitacionFields from "./NotificacionCitacionFields";
import NotificacionEntregaFields from "./NotificacionEntregaFields";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  editingNotificacion: InvolucradoNotificacion | null;
  involucrados: Involucrado[];
  yaNotificados: number[];
  tiposNotificacion: TipoNotificacion[];
  onSave: (data: NotificacionFormData) => Promise<{
    ok: boolean;
    error?: string;
  }>;
  isEditable?: boolean;
  notificacionesExistentes?: InvolucradoNotificacion[];
};

export default function NotificacionModal({
  isOpen,
  onClose,
  editingNotificacion,
  involucrados,
  yaNotificados,
  tiposNotificacion,
  onSave,
}: Props) {
  const form = useNotificacionForm({
    isOpen,
    editingNotificacion,
    onSave,
    onClose,
  });

  const {
    selectedFileCitacion,
    isSubmitting,
    isUploadingFiles,
    isEditing,
    errors,
    handleSave,
    handleClose,
  } = form;

  const involucradosDisponibles = involucrados.filter((inv) =>
    editingNotificacion
      ? inv.id === editingNotificacion.involucrado_id
      : !yaNotificados.includes(inv.id),
  );

  const hasDocumentoCitacion = isEditing
    ? editingNotificacion?.documento_citacion_id || selectedFileCitacion
    : selectedFileCitacion;

  const busy = isSubmitting || isUploadingFiles;

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      size="2xl"
      closeOnEsc={!busy}
      closeOnBackdrop={!busy}
      showCloseButton={!busy}
      className="select-none"
      bodyClassName="space-y-4"
      icon={
        <svg
          className="w-5 h-5 text-success"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>
      }
      title={editingNotificacion ? "Editar Notificación" : "Nueva Notificación"}
      subtitle="Complete la información de la notificación"
      footer={
        <>
          <button
            type="button"
            onClick={handleClose}
            className="btn btn-ghost"
            disabled={busy}
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleSave}
            className="btn btn-success text-white gap-2"
            disabled={busy}
          >
            {isUploadingFiles ? (
              <>
                <span className="loading loading-spinner loading-sm"></span>
                Subiendo archivos...
              </>
            ) : isSubmitting ? (
              <>
                <span className="loading loading-spinner loading-sm"></span>
                Guardando...
              </>
            ) : isEditing ? (
              <>
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
                Actualizar
              </>
            ) : (
              <>
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 4v16m8-8H4"
                  />
                </svg>
                Agregar
              </>
            )}
          </button>
        </>
      }
    >
      <NotificacionCitacionFields
        form={form}
        editingNotificacion={editingNotificacion}
        involucradosDisponibles={involucradosDisponibles}
      />

      <NotificacionEntregaFields
        form={form}
        editingNotificacion={editingNotificacion}
        tiposNotificacion={tiposNotificacion}
        hasDocumentoCitacion={hasDocumentoCitacion}
      />

      {/* Error general */}
      {errors.general && (
        <div className="alert alert-error">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="stroke-current shrink-0 h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span>{errors.general}</span>
        </div>
      )}
    </Modal>
  );
}
