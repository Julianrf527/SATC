import { useEffect, useState } from "react";
import { API_CONFIG, apiCall } from "../../../../utils/api";
import ConfirmDeleteModal from "./ConfirmDeleteModal";

type ComunicacionData = {
  id: number;
  numerado: string;
  fecha_numerado: string;
  fecha_envio: string;
  fecha_creacion: string;
  url_documento?: string;
};

type Props = {
  comunicacion: ComunicacionData | null;
  radicado: string;
  onEdit?: () => void;
  onDeleted?: () => void;
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  isEditable?: boolean;
};

export default function ComunicacionCard({
  comunicacion,
  radicado,
  onEdit,
  onDeleted,
  setToast,
  isEditable = true,
}: Props) {
  useEffect(() => {
    console.log("comunica", comunicacion);
  }, [comunicacion]);
  const [showPreview, setShowPreview] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const formatDateLong = (fecha: string | null) => {
    if (!fecha) return "No registrada";
    const [year, month, day] = fecha.split("-");
    const meses = [
      "enero",
      "febrero",
      "marzo",
      "abril",
      "mayo",
      "junio",
      "julio",
      "agosto",
      "septiembre",
      "octubre",
      "noviembre",
      "diciembre",
    ];
    return `${parseInt(day)} de ${meses[parseInt(month) - 1]} de ${year}`;
  };

  const formatNumerado = (numerado?: string | number) => {
    if (numerado === undefined || numerado === null) return "—"; // valor por defecto
    return numerado.toString().padStart(4, "0");
  };

  const isImageUrl = (url: string) => {
    return /\.(jpg|jpeg|png|gif|webp)$/i.test(url);
  };

  const isPdfUrl = (url: string) => {
    return /\.pdf$/i.test(url);
  };

  const openDocument = () => {
    if (comunicacion?.url_documento) {
      const BASE_URL = import.meta.env.VITE_API_URL;
      const url = `${BASE_URL}${API_CONFIG.ENDPOINTS.FILE_DOWNLOAD(
        comunicacion.url_documento,
      )}`;
      window.open(url, "_blank");
    }
  };

  const handleDeleteClick = () => {
    setShowDeleteModal(true);
  };

  const handleConfirmDelete = async () => {
    if (!comunicacion) return;

    setIsDeleting(true);
    try {
      const res = await apiCall(
        API_CONFIG.ENDPOINTS.FILE_COMUNICACION_DELETE(comunicacion.id),
        {
          method: "DELETE",
          body: JSON.stringify({ radicado }),
          headers: { "Content-Type": "application/json" },
        },
      );

      if (res.ok) {
        setToast({
          id: Date.now(),
          message: "Comunicación eliminada exitosamente",
          type: "success",
        });

        if (onDeleted) {
          onDeleted();
        }
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al eliminar la comunicación",
          type: "error",
        });
      }
    } catch (e) {
      console.error("Error eliminando comunicación:", e);
      setToast({
        id: Date.now(),
        message: "Error al eliminar la comunicación",
        type: "error",
      });
    } finally {
      setIsDeleting(false);
      setShowDeleteModal(false);
    }
  };

  // Estado vacío - sin comunicación
  if (!comunicacion?.id) {
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
                d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
              />
            </svg>
          </div>
          <h3 className="text-base font-medium text-base-content/70 mb-1">
            Sin comunicación
          </h3>
          <p className="text-sm text-base-content/60">
            No hay comunicación registrada
          </p>
        </div>
      </div>
    );
  }

  // Estado con comunicación
  return (
    <>
      <div className="bg-base-200 rounded-lg border border-base-300 p-6">
        <div className="flex items-start gap-4">
          {/* Contenido principal */}
          <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Documento - Numerado + Fecha combinados */}
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
                <p className="text-base font-semibold">
                  {formatNumerado(comunicacion.numerado)} del{" "}
                  {formatDateLong(comunicacion.fecha_numerado)}
                </p>
              </div>
            </div>

            {/* Fecha de Envío */}
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
                  Fecha de Envío
                </p>
                <p className="text-base font-semibold">
                  {formatDateLong(comunicacion.fecha_envio)}
                </p>
              </div>
            </div>
          </div>

          {/* Botones de acción a la derecha */}
          <div className="flex gap-2 flex-shrink-0">
            {/* Botón para abrir documento PDF */}
            {comunicacion.url_documento && (
              <button
                onClick={openDocument}
                className="btn btn-success btn-sm gap-1 px-2 tooltip"
                data-tip="Ver documento"
              >
                {isPdfUrl(comunicacion.url_documento) ? (
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
                  Comunicación
                </span>
              </button>
            )}

            {/* Botón de editar */}
            {isEditable && onEdit && (
              <button
                onClick={onEdit}
                className="btn btn-ghost btn-sm btn-square"
                title="Editar comunicación"
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
            )}

            {/* Botón de eliminar */}
            {isEditable && (
              <button
                onClick={handleDeleteClick}
                className="btn btn-ghost btn-sm btn-square text-error hover:bg-error/10"
                title="Eliminar comunicación"
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
            )}
          </div>
        </div>

        {/* Información adicional */}
        <div className="mt-4 pt-4 border-t border-base-300">
          <div className="flex items-center gap-2 text-sm text-base-content/60">
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
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span>
              Comunicación registrada el{" "}
              {formatDateLong(comunicacion.fecha_creacion)}
            </span>
          </div>
        </div>
      </div>

      {/* Modal de vista previa para imágenes */}
      {showPreview &&
        comunicacion.url_documento &&
        isImageUrl(comunicacion.url_documento) && (
          <div
            className="fixed inset-0 z-[999999] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
            onClick={() => setShowPreview(false)}
          >
            <div className="relative max-w-5xl max-h-[90vh]">
              <button
                onClick={() => setShowPreview(false)}
                className="absolute -top-12 right-0 btn btn-circle btn-ghost text-white hover:bg-white/20"
              >
                <svg
                  className="w-6 h-6"
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
              <img
                src={`${
                  import.meta.env.VITE_API_URL
                }${API_CONFIG.ENDPOINTS.FILE_DOWNLOAD(
                  comunicacion.url_documento,
                )}`}
                alt="Vista previa del documento"
                className="max-w-full max-h-[90vh] rounded-lg shadow-2xl"
                onClick={(e) => e.stopPropagation()}
              />
            </div>
          </div>
        )}

      {/* Modal de confirmación de eliminación */}
      <ConfirmDeleteModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleConfirmDelete}
        type="comunicacion"
        itemIdentifier={comunicacion.numerado?.toString()}
        isDeleting={isDeleting}
      />
    </>
  );
}
