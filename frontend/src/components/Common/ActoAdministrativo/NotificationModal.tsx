import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import type {
  TipoNotificacion,
  InvolucradoNotificacion,
} from "../../../types/sancionatorioApp";
import type { Involucrado } from "../../../types/involucradoApp";
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
  const [theme, setTheme] = useState<string>("emerald");

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

  useEffect(() => {
    if (isOpen) {
      const currentTheme =
        document.querySelector("[data-theme]")?.getAttribute("data-theme") ||
        "emerald";
      setTheme(currentTheme);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const involucradosDisponibles = involucrados.filter((inv) =>
    editingNotificacion
      ? inv.id === editingNotificacion.involucrado_id
      : !yaNotificados.includes(inv.id),
  );

  const hasDocumentoCitacion = isEditing
    ? editingNotificacion?.documento_citacion_id || selectedFileCitacion
    : selectedFileCitacion;

  const modalContent = (
    <div
      data-theme={theme}
      className="fixed inset-0 z-[999999] flex items-center justify-center select-none bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={handleClose}
    >
      <div
        className="bg-base-100 rounded-2xl w-full max-w-2xl mx-4 shadow-2xl border border-base-300 animate-in zoom-in-95 duration-200 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="relative px-6 py-5 border-b border-base-300">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-success/10 rounded-xl flex items-center justify-center">
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
            </div>
            <div>
              <h3 className="font-bold text-lg text-base-content">
                {editingNotificacion
                  ? "Editar Notificación"
                  : "Nueva Notificación"}
              </h3>
              <p className="text-xs text-base-content/60">
                Complete la información de la notificación
              </p>
            </div>
          </div>

          <button
            onClick={handleClose}
            className="absolute top-4 right-4 btn btn-ghost btn-sm btn-circle"
            disabled={isSubmitting || isUploadingFiles}
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4">
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

          {/* Botones */}
          <div className="flex justify-end space-x-2 pt-4 border-t border-base-300">
            <button
              type="button"
              onClick={handleClose}
              className="btn btn-ghost"
              disabled={isSubmitting || isUploadingFiles}
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="btn btn-success text-white gap-2"
              disabled={isSubmitting || isUploadingFiles}
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
          </div>
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
