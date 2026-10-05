import { useState } from "react";
import type {
  InvolucradoNotificacion,
  TipoNotificacion,
} from "@shared/types/sancionatorio";
import type { Involucrado } from "@shared/types/involucrado";
import { formatDate } from "@shared/lib/format";
import ConfirmDeleteModal from "./ConfirmDeleteModal";
import InfoField from "./InfoField";
import { INFO_ICONS } from "./infoIcons";

const SIN_FECHA = { fallback: "No registrada" };

export default function NotificacionesTable({
  notificaciones,
  involucrados,
  tiposNotificacion,
  onEdit,
  onDelete,
  onViewDocument,
  isEditable = true,
}: {
  notificaciones: InvolucradoNotificacion[];
  involucrados: Involucrado[];
  tiposNotificacion: TipoNotificacion[];
  onEdit: (notificacion: InvolucradoNotificacion) => void;
  onDelete: (id: number) => void;
  onViewDocument: (fileId: number) => void;
  isEditable?: boolean;
}) {
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [notificacionToDelete, setNotificacionToDelete] = useState<
    number | null
  >(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const formatDocumentNumber = (involucrado: Involucrado): string => {
    if (
      involucrado.tipo_documento === "NIT" &&
      involucrado.digito_verificacion
    ) {
      return `${involucrado.numero_documento}-${involucrado.digito_verificacion}`;
    }
    return involucrado.numero_documento.toString();
  };

  const getInvolucradoName = (id: number) => {
    const involucrado = involucrados.find((i) => i.id === id);
    return involucrado
      ? {
          tipo: involucrado.tipo_documento,
          numero: formatDocumentNumber(involucrado),
          nombre: involucrado.nombre,
        }
      : null;
  };

  const getTipoNotificacionName = (id: number | null) => {
    if (!id) return null;
    const tipo = tiposNotificacion.find((t) => t.id === id);
    return tipo ? tipo.nombre : null;
  };

  const handleDeleteClick = (id: number) => {
    setNotificacionToDelete(id);
    setDeleteModalOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (notificacionToDelete === null) return;
    setIsDeleting(true);
    try {
      await onDelete(notificacionToDelete);
      setDeleteModalOpen(false);
      setNotificacionToDelete(null);
    } catch {
      // El hook padre ya notifica el error con un toast.
    } finally {
      setIsDeleting(false);
    }
  };

  const handleCancelDelete = () => {
    setDeleteModalOpen(false);
    setNotificacionToDelete(null);
  };

  if (!notificaciones || notificaciones.length === 0) {
    return (
      <div className="bg-base-200 rounded-lg border border-base-300 p-6">
        <div className="text-center py-8">
          <div className="w-16 h-16 bg-base-300 rounded-full flex items-center justify-center mb-4 mx-auto">
            <svg
              className="w-8 h-8 text-base-content/40"
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
          <h3 className="text-base font-medium text-base-content/70 mb-1">
            Sin notificaciones
          </h3>
          <p className="text-sm text-base-content/60">
            No hay notificaciones registradas
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-3">
        {notificaciones.map((notificacion) => {
          if (!notificacion) return null;

          const involucrado = getInvolucradoName(notificacion.involucrado_id);
          const tipoNotificacion = getTipoNotificacionName(
            notificacion.tipo_notificacion_id,
          );

          return (
            <div
              key={notificacion.id || Math.random()} // Fallback seguro para key
              className="bg-base-200 rounded-lg border border-base-300 hover:border-success/30 transition-all p-4"
            >
              {/* Header con avatar, nombre e info del involucrado + badge y botones */}
              <div className="flex items-start justify-between gap-4 mb-3">
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <div className="avatar avatar-placeholder">
                    <div className="w-10 h-10 rounded-full bg-info text-white !grid !place-items-center overflow-hidden">
                      <span className="text-sm font-bold leading-none">
                        {involucrado
                          ? involucrado.nombre
                              .split(" ")
                              .map((n) => n?.[0] ?? "")
                              .join("")
                              .substring(0, 2)
                              .toUpperCase()
                          : "?"}
                      </span>
                    </div>
                  </div>

                  <div className="min-w-0 flex-1">
                    <h4 className="font-semibold truncate">
                      {involucrado ? involucrado.nombre : "No encontrado"}
                    </h4>
                    {involucrado && (
                      <p className="text-sm text-base-content/70">
                        <span className="font-medium">{involucrado.tipo}:</span>{" "}
                        <span className="font-mono">{involucrado.numero}</span>
                      </p>
                    )}
                  </div>
                </div>

                {/* Badge de estado y botones de acción */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  <div
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold text-white ${
                      notificacion.notificacion_exitosa
                        ? "bg-success"
                        : "bg-warning"
                    }`}
                  >
                    {notificacion.notificacion_exitosa ? (
                      <>
                        <div className="w-2 h-2 rounded-full bg-white animate-pulse" />
                        <span>Notificado</span>
                      </>
                    ) : (
                      <>
                        <div className="w-2 h-2 rounded-full bg-white animate-pulse" />
                        <span>Pendiente</span>
                      </>
                    )}
                  </div>

                  {/* Botón para ver documento de citación */}
                  {notificacion.documento_citacion_id ? (
                    <button
                      onClick={() =>
                        onViewDocument(notificacion.documento_citacion_id)
                      }
                      className="btn btn-success btn-sm gap-1 px-2 tooltip"
                      data-tip="Ver documento de citación"
                    >
                      <svg
                        className="w-4 h-4 text-white"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" />
                      </svg>
                      <span className="text-xs font-medium text-white">
                        Citación
                      </span>
                    </button>
                  ) : (
                    <div
                      className="badge badge-warning badge-sm gap-1 px-2 tooltip"
                      data-tip="No hay documento de citación"
                    >
                      <svg
                        className="w-3 h-3"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                          clipRule="evenodd"
                        />
                      </svg>
                      <span className="text-xs">Sin citación</span>
                    </div>
                  )}

                  {/* Botón para ver documento de notificación */}
                  {notificacion.documento_notificacion_id && (
                    <button
                      onClick={() =>
                        notificacion.documento_notificacion_id &&
                        onViewDocument(notificacion.documento_notificacion_id)
                      }
                      className="btn btn-success btn-sm gap-1 px-2 tooltip"
                      data-tip="Ver documento de notificación"
                    >
                      <svg
                        className="w-4 h-4 text-white"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" />
                      </svg>
                      <span className="text-xs font-medium text-white">
                        Notificación
                      </span>
                    </button>
                  )}

                  {isEditable && (
                    <>
                      <button
                        onClick={() => onEdit(notificacion)}
                        className="btn btn-ghost btn-sm btn-square"
                        title="Editar notificación"
                      >
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
                            d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                          />
                        </svg>
                      </button>
                      <button
                        onClick={() => handleDeleteClick(notificacion.id)}
                        className="btn btn-ghost btn-sm btn-square text-error hover:bg-error/10"
                        title="Eliminar notificación"
                      >
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
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                          />
                        </svg>
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Grid de información (4 secciones) */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                <InfoField iconPath={INFO_ICONS.documento} tone="success" label="Documento">
                  {notificacion.numerado} del{" "}
                  {formatDate(notificacion.fecha_numerado, SIN_FECHA)}
                </InfoField>
                <InfoField iconPath={INFO_ICONS.correo} tone="warning" label="Fecha Envío">
                  {formatDate(notificacion.fecha_envio_citacion, SIN_FECHA)}
                </InfoField>
                <InfoField iconPath={INFO_ICONS.check} tone="info" label="Fecha Constancia">
                  {formatDate(notificacion.fecha_constancia_citacion, SIN_FECHA)}
                </InfoField>
                <InfoField iconPath={INFO_ICONS.portapapeles} tone="primary" label="Tipo Notificación">
                  {tipoNotificacion || "No especificado"}
                </InfoField>
              </div>
            </div>
          );
        })}
      </div>

      {/* Modal de confirmación de eliminación */}
      <ConfirmDeleteModal
        isOpen={deleteModalOpen}
        onClose={handleCancelDelete}
        onConfirm={handleConfirmDelete}
        type="notificacion"
        itemIdentifier={notificacionToDelete ?? undefined}
        isDeleting={isDeleting}
      />
    </>
  );
}
