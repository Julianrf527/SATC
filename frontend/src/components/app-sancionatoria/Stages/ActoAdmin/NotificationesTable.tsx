import { useState } from "react";
import type {
  Involved,
  InvolucradoNotificacion,
  TipoNotificacion,
} from "../../../../types";
import ConfirmDeleteModal from "./ConfirmDeleteModal";

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
  involucrados: Involved[];
  tiposNotificacion: TipoNotificacion[];
  onEdit: (notificacion: InvolucradoNotificacion) => void;
  onDelete: (id: number) => void;
  onViewDocument: (url: string) => void;
  isEditable?: boolean;
}) {
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [notificacionToDelete, setNotificacionToDelete] = useState<
    number | null
  >(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Función para formatear el número de documento con DV para NITs
  const formatDocumentNumber = (involucrado: Involved): string => {
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

  const formatDate = (fecha: string | null) => {
    if (!fecha) return "No registrada";
    if (typeof fecha !== "string") return "No registrada";
    const parts = fecha.split("-");
    if (parts.length !== 3) return "No registrada";
    const [year, month, day] = parts;
    if (!year || !month || !day) return "No registrada";
    return `${day.padStart(2, "0")}/${month.padStart(2, "0")}/${year}`;
  };

  const isPdfUrl = (url: string) => {
    return /\.pdf$/i.test(url);
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
    } catch (error) {
      console.error("Error al eliminar notificación:", error);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleCancelDelete = () => {
    setDeleteModalOpen(false);
    setNotificacionToDelete(null);
  };

  // Validación de seguridad para el array completo
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
                  <div className="avatar placeholder">
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
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold ${
                      notificacion.notificacion_exitosa
                        ? "bg-success/10 text-success border border-success/30"
                        : "bg-warning/10 text-warning border border-warning/30"
                    }`}
                  >
                    {notificacion.notificacion_exitosa ? (
                      <>
                        <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
                        <span>Notificada</span>
                      </>
                    ) : (
                      <>
                        <div className="w-2 h-2 rounded-full bg-warning animate-pulse" />
                        <span>Pendiente</span>
                      </>
                    )}
                  </div>

                  {/* Botón para ver documento de citación */}
                  {notificacion.url_doc_citacion ? (
                    <button
                      onClick={() =>
                        onViewDocument(notificacion.url_doc_citacion!)
                      }
                      className="btn btn-success btn-sm gap-1 px-2 tooltip"
                      data-tip="Ver documento de citación"
                    >
                      {isPdfUrl(notificacion.url_doc_citacion) ? (
                        <svg
                          className="w-4 h-4 text-white"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" />
                        </svg>
                      ) : (
                        <svg
                          className="w-4 h-4 text-white"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                          />
                        </svg>
                      )}
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
                  {notificacion.url_documento && (
                    <button
                      onClick={() => onViewDocument(notificacion.url_documento)}
                      className="btn btn-success btn-sm gap-1 px-2 tooltip"
                      data-tip="Ver documento de notificación"
                    >
                      {isPdfUrl(notificacion.url_documento) ? (
                        <svg
                          className="w-4 h-4 text-white"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" />
                        </svg>
                      ) : (
                        <svg
                          className="w-4 h-4 text-white"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                          />
                        </svg>
                      )}
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
                {/* Documento */}
                <div className="flex items-start gap-3 min-w-0">
                  <div className="w-10 h-10 bg-success/10 rounded-full flex items-center justify-center flex-shrink-0">
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
                        d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                      />
                    </svg>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs text-base-content/60 font-medium mb-1">
                      Documento
                    </p>
                    <p className="text-sm font-semibold">
                      {notificacion.numerado} del{" "}
                      {formatDate(notificacion.fecha_numerado)}
                    </p>
                  </div>
                </div>

                {/* Fecha Envío */}
                <div className="flex items-start gap-3 min-w-0">
                  <div className="w-10 h-10 bg-warning/10 rounded-full flex items-center justify-center flex-shrink-0">
                    <svg
                      className="w-5 h-5 text-warning"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                      />
                    </svg>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs text-base-content/60 font-medium mb-1">
                      Fecha Envío
                    </p>
                    <p className="text-sm font-semibold">
                      {formatDate(notificacion.fecha_envio_citacion)}
                    </p>
                  </div>
                </div>

                {/* Fecha Constancia */}
                <div className="flex items-start gap-3 min-w-0">
                  <div className="w-10 h-10 bg-info/10 rounded-full flex items-center justify-center flex-shrink-0">
                    <svg
                      className="w-5 h-5 text-info"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs text-base-content/60 font-medium mb-1">
                      Fecha Constancia
                    </p>
                    <p className="text-sm font-semibold">
                      {formatDate(notificacion.fecha_constancia_citacion)}
                    </p>
                  </div>
                </div>

                {/* Tipo de Notificación */}
                <div className="flex items-start gap-3 min-w-0">
                  <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center flex-shrink-0">
                    <svg
                      className="w-5 h-5 text-primary"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
                      />
                    </svg>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs text-base-content/60 font-medium mb-1">
                      Tipo Notificación
                    </p>
                    <p className="text-sm font-semibold">
                      {tipoNotificacion || "No especificado"}
                    </p>
                  </div>
                </div>
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
