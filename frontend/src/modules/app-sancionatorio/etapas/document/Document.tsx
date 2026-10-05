import { useState } from "react";
import { apiCall, API_CONFIG, formatApiErrorDetail } from "@shared/lib/api";
import { openDocumentById } from "@shared/lib/documentViewer";
import { formatDate } from "@shared/lib/format";
import type { DocumentoAnexo, DocumentoAnexoPayload, SetToast } from "../../types";
import Icono from "../comun/Icono";
import { ICONOS, PDF_RELLENO_24 } from "../comun/iconos";
import DocumentoModal from "./DocumentModal";
import ConfirmDeleteDocumentoModal from "./ConfirmDeleteDocumentModal";

type Props = {
  documentos: DocumentoAnexo[];
  etapaId: number;
  tipoEtapa: string;
  tiposDocumento: string[];
  setToast: SetToast;
  isEditable?: boolean;
  onDocumentosUpdate?: (documentos: DocumentoAnexo[]) => void;
};

/** Documentos anexos de una etapa: listado + crear/editar/eliminar. */
export default function Document({
  documentos,
  etapaId,
  tipoEtapa,
  tiposDocumento,
  setToast,
  isEditable = true,
  onDocumentosUpdate,
}: Props) {
  const [localDocumentos, setLocalDocumentos] = useState<DocumentoAnexo[]>(documentos);
  const [showDocumentoModal, setShowDocumentoModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [editingDocumento, setEditingDocumento] = useState<DocumentoAnexo | null>(null);
  const [deletingDocumento, setDeletingDocumento] = useState<DocumentoAnexo | null>(null);

  const actualizar = (lista: DocumentoAnexo[]) => {
    setLocalDocumentos(lista);
    onDocumentosUpdate?.(lista);
  };

  const handleSaveDocumento = async (
    payload: DocumentoAnexoPayload,
  ): Promise<{ ok: boolean; error?: string }> => {
    try {
      const isEditing = !!editingDocumento;
      const endpoint = isEditing
        ? API_CONFIG.ENDPOINTS.FILE_PUT_DOC_ATTACHED(etapaId, editingDocumento.id)
        : API_CONFIG.ENDPOINTS.FILE_POST_DOC_ATTACHED(etapaId);

      const documentoAnexoId = payload.documento_anexo_id ?? editingDocumento?.documento_anexo_id;
      if (!documentoAnexoId) {
        return { ok: false, error: "No se encontró el documento adjunto" };
      }

      const res = await apiCall(endpoint, {
        method: isEditing ? "PUT" : "POST",
        body: JSON.stringify({
          nombre: payload.nombre,
          documento_anexo_id: documentoAnexoId,
          etapa_tipo: tipoEtapa,
        }),
      });

      if (!res.ok) {
        return { ok: false, error: formatApiErrorDetail(res.detail, "Error al guardar documento") };
      }

      const documentoData: DocumentoAnexo = res.documento_anexo;
      actualizar(
        isEditing
          ? localDocumentos.map((doc) => (doc.id === documentoData.id ? documentoData : doc))
          : [documentoData, ...localDocumentos],
      );
      setToast({
        id: Date.now(),
        message: isEditing ? "Documento actualizado exitosamente" : "Documento agregado exitosamente",
        type: "success",
      });
      return { ok: true };
    } catch (e) {
      if (import.meta.env.DEV) console.error("Error guardando documento:", e);
      return { ok: false, error: "Error al guardar documento" };
    }
  };

  const handleDeleteDocumento = async () => {
    try {
      if (!deletingDocumento) return;
      const res = await apiCall(
        API_CONFIG.ENDPOINTS.FILE_DELETE_DOC_ATTACHED(etapaId, deletingDocumento.id),
        { method: "DELETE" },
      );
      if (res.ok) {
        actualizar(localDocumentos.filter((doc) => doc.id !== deletingDocumento.id));
        setToast({ id: Date.now(), message: "Documento eliminado exitosamente", type: "success" });
      } else {
        setToast({ id: Date.now(), message: res.detail || "Error al eliminar documento", type: "error" });
      }
    } catch (e) {
      if (import.meta.env.DEV) console.error("Error eliminando documento:", e);
      setToast({ id: Date.now(), message: "Error al eliminar documento", type: "error" });
    } finally {
      setShowDeleteModal(false);
      setDeletingDocumento(null);
    }
  };

  const sortedDocumentos = [...localDocumentos].sort(
    (a, b) => new Date(b.fecha_subida).getTime() - new Date(a.fecha_subida).getTime(),
  );

  return (
    <div className="card bg-base-100 shadow-md border border-base-300">
      <div className="card-body p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">Documentos</h2>
          {isEditable && (
            <button
              onClick={() => {
                setEditingDocumento(null);
                setShowDocumentoModal(true);
              }}
              className="btn btn-success text-white btn-sm gap-2"
            >
              <Icono d={ICONOS.mas} />
              Agregar Documento
            </button>
          )}
        </div>

        {sortedDocumentos.length === 0 ? (
          <div className="text-center py-8 bg-base-200 rounded-lg border-2 border-dashed border-base-300">
            <div className="w-12 h-12 bg-base-300 rounded-full flex items-center justify-center mb-3 mx-auto">
              <Icono d={ICONOS.documento} className="w-6 h-6 text-base-content/40" />
            </div>
            <h3 className="text-sm font-medium text-base-content/70 mb-2">Sin documentos</h3>
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
                      <p className="font-semibold text-base truncate">{documento.nombre}</p>
                      <p className="text-xs text-base-content/60 mt-1">
                        {formatDate(documento.fecha_subida, { style: "long" })}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 ml-4">
                  {isEditable && (
                    <>
                      <button
                        onClick={() => {
                          setEditingDocumento(documento);
                          setShowDocumentoModal(true);
                        }}
                        className="btn btn-ghost btn-sm btn-square"
                        title="Editar documento"
                      >
                        <Icono d={ICONOS.editar} />
                      </button>
                      <button
                        onClick={() => {
                          setDeletingDocumento(documento);
                          setShowDeleteModal(true);
                        }}
                        className="btn btn-ghost btn-sm btn-square text-error hover:bg-error/10"
                        title="Eliminar documento"
                      >
                        <Icono d={ICONOS.papelera} />
                      </button>
                    </>
                  )}

                  <button
                    onClick={() => openDocumentById(documento.documento_anexo_id)}
                    className="btn btn-success btn-sm gap-1 px-2 tooltip"
                    data-tip="Ver documento PDF"
                  >
                    <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor">
                      <path d={PDF_RELLENO_24} />
                    </svg>
                    <span className="text-xs font-medium text-white">Documento</span>
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
              onSave={handleSaveDocumento}
              editDocumento={editingDocumento}
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
