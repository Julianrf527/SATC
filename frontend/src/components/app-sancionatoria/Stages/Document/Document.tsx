import { useState } from "react";
import { apiCall, API_CONFIG, BASE_URL } from "../../../../utils/api";
import DocumentoModal from "./DocumentModal";
import ConfirmDeleteDocumentoModal from "./ConfirmDeleteDocumentModal";

type DocumentoData = {
  id: number;
  nombre: string;
  url_documento: string;
  fecha_subida: string;
};

type Props = {
  documentos: DocumentoData[];
  etapaId: number;
  radicado: string;
  idAuxiliar: number;
  tipoEtapa: string;
  tiposDocumento: string[];
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  isEditable?: boolean;
  onDocumentosUpdate?: (documentos: DocumentoData[]) => void;
};

export default function Document({
  documentos,
  etapaId,
  radicado,
  tiposDocumento,
  setToast,
  isEditable = true,
  onDocumentosUpdate,
}: Props) {
  const [localDocumentos, setLocalDocumentos] =
    useState<DocumentoData[]>(documentos);
  const [showDocumentoModal, setShowDocumentoModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [editingDocumento, setEditingDocumento] =
    useState<DocumentoData | null>(null);
  const [deletingDocumento, setDeletingDocumento] =
    useState<DocumentoData | null>(null);

  const formatDate = (fecha: string) => {
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

  const handleViewFile = (urlDocumento: string) => {
    // TODO: Migrar a usar file_id en lugar de URL string
    const fileId = parseInt(urlDocumento) || 0;
    const url = `${BASE_URL}${API_CONFIG.ENDPOINTS.FILE_DOWNLOAD(fileId)}`;
    window.open(url, "_blank");
  };

  const handleSaveDocumento = async (
    formData: FormData,
  ): Promise<{ ok: boolean; error?: string }> => {
    try {
      const isEditing = !!editingDocumento;
      const endpoint = isEditing
        ? `${API_CONFIG.ENDPOINTS.FILE_UPLOAD}/${editingDocumento.id}` // TODO: Crear endpoint específico
        : API_CONFIG.ENDPOINTS.FILE_UPLOAD;

      const method = isEditing ? "PUT" : "POST";

      // Agregar parámetros necesarios
      if (!formData.has("etapa_id")) {
        formData.append("etapa_id", etapaId.toString());
      }
      if (!formData.has("radicado")) {
        formData.append("radicado", radicado);
      }

      const res = await apiCall(endpoint, {
        method,
        body: formData,
      });

      if (res.ok) {
        const documentoData = res.data;

        // Actualizar estado local
        let updatedDocumentos: DocumentoData[];
        if (isEditing) {
          updatedDocumentos = localDocumentos.map((doc) =>
            doc.id === documentoData.id ? documentoData : doc,
          );
        } else {
          updatedDocumentos = [documentoData, ...localDocumentos];
        }

        setLocalDocumentos(updatedDocumentos);

        if (onDocumentosUpdate) {
          onDocumentosUpdate(updatedDocumentos);
        }

        setToast({
          id: Date.now(),
          message: isEditing
            ? "Documento actualizado exitosamente"
            : "Documento agregado exitosamente",
          type: "success",
        });

        return { ok: true };
      } else {
        let errorMessage = "Error al guardar documento";

        if (res.detail) {
          if (typeof res.detail === "string") {
            errorMessage = res.detail;
          } else if (Array.isArray(res.detail)) {
            errorMessage = res.detail.map((err: any) => err.msg).join(", ");
          }
        }

        /* console.error("Error del backend:", res); */
        return { ok: false, error: errorMessage };
      }
    } catch (e) {
      console.error("Error guardando documento:", e);
      return { ok: false, error: "Error al guardar documento" };
    }
  };

  const handleDeleteDocumento = async () => {
    try {
      if (!deletingDocumento) return;

      const res = await apiCall(
        `${API_CONFIG.ENDPOINTS.FILE(deletingDocumento.id)}?radicado=${radicado}`, // TODO: Crear endpoint específico de delete
        {
          method: "DELETE",
        },
      );

      if (res.ok) {
        // Actualizar estado local
        const updatedDocumentos = localDocumentos.filter(
          (doc) => doc.id !== deletingDocumento.id,
        );
        setLocalDocumentos(updatedDocumentos);

        if (onDocumentosUpdate) {
          onDocumentosUpdate(updatedDocumentos);
        }

        setToast({
          id: Date.now(),
          message: "Documento eliminado exitosamente",
          type: "success",
        });
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al eliminar documento",
          type: "error",
        });
      }
    } catch (e) {
      console.error("Error eliminando documento:", e);
      setToast({
        id: Date.now(),
        message: "Error al eliminar documento",
        type: "error",
      });
    } finally {
      setShowDeleteModal(false);
      setDeletingDocumento(null);
    }
  };

  const handleAddDocumento = () => {
    setEditingDocumento(null);
    setShowDocumentoModal(true);
  };

  const handleEditDocumento = (documento: DocumentoData) => {
    setEditingDocumento(documento);
    setShowDocumentoModal(true);
  };

  const handleOpenDeleteModal = (documento: DocumentoData) => {
    setDeletingDocumento(documento);
    setShowDeleteModal(true);
  };

  // Ordenar documentos por fecha de subida (más reciente primero)
  const sortedDocumentos = [...localDocumentos].sort(
    (a, b) =>
      new Date(b.fecha_subida).getTime() - new Date(a.fecha_subida).getTime(),
  );

  return (
    <div className="card bg-base-100 shadow-md border border-base-300">
      <div className="card-body p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">Documentos</h2>
          {isEditable && (
            <button
              onClick={handleAddDocumento}
              className="btn btn-success text-white btn-sm gap-2"
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
                  d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                />
              </svg>
              Agregar Documento
            </button>
          )}
        </div>

        {sortedDocumentos.length === 0 ? (
          <div className="text-center py-8 bg-base-200 rounded-lg border-2 border-dashed border-base-300">
            <div className="w-12 h-12 bg-base-300 rounded-full flex items-center justify-center mb-3 mx-auto">
              <svg
                className="w-6 h-6 text-base-content/40"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            <h3 className="text-sm font-medium text-base-content/70 mb-2">
              Sin documentos
            </h3>
            <p className="text-xs text-base-content/60 mb-3">
              No hay documentos registrados para esta etapa
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {sortedDocumentos.map((documento) => (
              <div
                key={documento.id}
                className="flex items-center justify-between p-4 bg-base-200 rounded-lg border border-base-300 hover:bg-base-300/50 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-base truncate">
                        {documento.nombre}
                      </p>
                      <p className="text-xs text-base-content/60 mt-1">
                        {formatDate(documento.fecha_subida)}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 ml-4">
                  {isEditable && (
                    <>
                      <button
                        onClick={() => handleEditDocumento(documento)}
                        className="btn btn-ghost btn-sm btn-square"
                        title="Editar documento"
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
                        onClick={() => handleOpenDeleteModal(documento)}
                        className="btn btn-ghost btn-sm btn-square text-error hover:bg-error/10"
                        title="Eliminar documento"
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

                  <button
                    onClick={() => handleViewFile(documento.url_documento)}
                    className="btn btn-success btn-sm gap-1 px-2 tooltip"
                    data-tip="Ver documento PDF"
                  >
                    <svg
                      className="w-4 h-4 text-white"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                    >
                      <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M15.5,15.5L13,19L11.5,15.5L8,14L11.5,12.5L13,9L14.5,12.5L18,14L15.5,15.5M13,3.5L17.5,8H13V3.5Z" />
                    </svg>
                    <span className="text-xs font-medium text-white">
                      Documento
                    </span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {isEditable && (
          <>
            <DocumentoModal
              isOpen={showDocumentoModal}
              onClose={() => {
                setShowDocumentoModal(false);
                setEditingDocumento(null);
              }}
              onSave={handleSaveDocumento as any} // TODO: Arreglar tipos después de migración completa
              editDocumento={editingDocumento as any} // TODO: Arreglar tipos después de migración completa
              tiposDocumento={tiposDocumento}
            />

            <ConfirmDeleteDocumentoModal
              isOpen={showDeleteModal}
              onClose={() => {
                setShowDeleteModal(false);
                setDeletingDocumento(null);
              }}
              onConfirm={handleDeleteDocumento}
              type="documento"
            />
          </>
        )}
      </div>
    </div>
  );
}
