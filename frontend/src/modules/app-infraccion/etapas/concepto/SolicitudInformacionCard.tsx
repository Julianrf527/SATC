import { useRef, useState, useMemo } from "react";
import { FileText, CalendarDays } from "lucide-react";
import {
  uploadFileToDocuments,
  generateDocumentFileName,
} from "@shared/lib/fileUpload";
import { openDocumentById } from "@shared/lib/documentViewer";
import CustomDateInput from "@shared/ui/form/CustomDateInput";
import { Modal } from "@shared/ui";
import type { SolicitudInformacion } from "../../types";
import {
  useEliminarSolicitudInformacionMutation,
  useGuardarSolicitudInformacionMutation,
} from "../../api/etapas";
import { detalleError } from "../../api/errors";

const RADICADO_REGEX = /^\d{4}EE\d{4,5}$/;

type Props = {
  etapaConceptoId: number;
  expedienteId: number;
  solicitud: SolicitudInformacion | null;
  isEditable: boolean;
  setToast: (t: { id: number; message: string; type: "success" | "error" }) => void;
};

const mensajeError = (err: unknown, fallback: string) =>
  detalleError(err) ?? (err instanceof Error && err.message ? err.message : fallback);

export default function SolicitudInformacionCard({
  etapaConceptoId,
  expedienteId,
  solicitud,
  isEditable,
  setToast,
}: Props) {
  const [showForm, setShowForm] = useState(false);
  const [radicado, setRadicado] = useState(solicitud?.radicado ?? "");
  const [fechaRadicado, setFechaRadicado] = useState(solicitud?.fecha_radicado ?? "");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const guardarSolicitud = useGuardarSolicitudInformacionMutation(expedienteId, etapaConceptoId);
  const eliminarSolicitud = useEliminarSolicitudInformacionMutation(expedienteId);
  const isDeleting = eliminarSolicitud.isPending;

  const radicadoValido = useMemo(() => radicado === "" || RADICADO_REGEX.test(radicado), [radicado]);
  const hoy = new Date().toISOString().split("T")[0];

  const resetCampos = () => {
    setShowForm(false);
    if (solicitud) {
      setRadicado(solicitud.radicado);
      setFechaRadicado(solicitud.fecha_radicado);
    } else {
      setRadicado("");
      setFechaRadicado("");
    }
    setSelectedFile(null);
    if (fileRef.current) fileRef.current.value = "";
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validar ANTES de subir el PDF (antes quedaba huérfano en app-docs si fallaba).
    if (!RADICADO_REGEX.test(radicado.trim())) {
      setToast({ id: Date.now(), message: "El radicado no cumple el formato requerido (ej: 2024EE0001)", type: "error" });
      return;
    }
    if (!fechaRadicado) {
      setToast({ id: Date.now(), message: "Seleccione la fecha de radicado", type: "error" });
      return;
    }
    if (!selectedFile && !solicitud?.archivo_solicitud_id) {
      setToast({ id: Date.now(), message: "Debe adjuntar el documento de la solicitud", type: "error" });
      return;
    }

    setIsSubmitting(true);
    try {
      let archivoId = solicitud?.archivo_solicitud_id;
      if (selectedFile) {
        setIsUploading(true);
        archivoId = await uploadFileToDocuments(
          selectedFile,
          generateDocumentFileName("SOLICITUD_INFO", radicado, fechaRadicado),
        );
        setIsUploading(false);
      }

      await guardarSolicitud.mutateAsync({
        solicitudId: solicitud?.id ?? null,
        payload: { radicado, fecha_radicado: fechaRadicado, archivo_solicitud_id: archivoId as number },
      });
      setToast({ id: Date.now(), message: solicitud ? "Solicitud actualizada" : "Solicitud registrada", type: "success" });
      setShowForm(false);
    } catch (err) {
      setToast({ id: Date.now(), message: mensajeError(err, "Error al guardar la solicitud"), type: "error" });
    } finally {
      setIsSubmitting(false);
      setIsUploading(false);
    }
  };

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
          {!showForm && isEditable && solicitud && (
            <div className="flex items-center gap-1">
              <button
                className="btn btn-ghost btn-sm gap-2 text-tono-info hover:bg-info/10"
                onClick={() => setShowForm(true)}
                disabled={isSubmitting}
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
                disabled={isSubmitting}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Eliminar
              </button>
            </div>
          )}
          {!showForm && !solicitud && isEditable && (
            <button
              className="btn btn-info btn-sm text-white gap-2"
              onClick={() => setShowForm(true)}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              Agregar Solicitud
            </button>
          )}
        </div>

        {/* Vista datos */}
        {!showForm && solicitud && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 p-4 bg-base-200/40 rounded-xl">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-info/10 rounded-lg flex items-center justify-center flex-shrink-0">
                <FileText className="text-tono-info" size={18} />
              </div>
              <div>
                <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">Radicado</p>
                <p className="text-sm font-semibold mt-0.5">{solicitud.radicado}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-info/10 rounded-lg flex items-center justify-center flex-shrink-0">
                <CalendarDays className="text-tono-info" size={18} />
              </div>
              <div>
                <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">Fecha Radicado</p>
                <p className="text-sm font-semibold mt-0.5">{solicitud.fecha_radicado}</p>
              </div>
            </div>
            <div className="flex items-end">
              <button
                className="btn btn-success btn-sm gap-1"
                onClick={() => openDocumentById(solicitud.archivo_solicitud_id)}
              >
                <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M13,3.5L17.5,8H13V3.5Z" />
                </svg>
                <span className="text-xs text-white">Ver documento</span>
              </button>
            </div>
          </div>
        )}

        {/* Formulario */}
        {showForm && isEditable && (
          <form onSubmit={handleSave} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="flex flex-col">
                <label className="label">
                  <span className="text-sm text-base-content font-medium">Radicado *</span>
                  <span className="text-xs text-base-content/60">ej: 2024EE0001</span>
                </label>
                <input
                  type="text"
                  className={`input w-full ${radicado && !radicadoValido ? "input-error" : radicado && radicadoValido ? "input-success" : ""}`}
                  value={radicado}
                  onChange={(e) => setRadicado(e.target.value.toUpperCase())}
                  disabled={isSubmitting}
                  maxLength={11}
                  placeholder="2024EE0001"
                  required
                />
                {radicado && !radicadoValido && (
                  <label className="label">
                    <span className="text-xs text-error">Formato inválido. Use: 4 dígitos + EE + 4 o 5 dígitos</span>
                  </label>
                )}
              </div>
              <div className="flex flex-col">
                <label className="label">
                  <span className="text-sm text-base-content font-medium">Fecha Radicado *</span>
                </label>
                <CustomDateInput
                  value={fechaRadicado}
                  onChange={setFechaRadicado}
                  max={hoy}
                  disabled={isSubmitting}
                />
              </div>
            </div>

            <div className="flex flex-col">
              <label className="label">
                <span className="text-sm text-base-content font-medium">
                  Documento PDF{!solicitud && <span className="text-error"> *</span>}
                  {solicitud && <span className="text-xs text-base-content/60 ml-2">(opcional: reemplazar)</span>}
                </span>
              </label>
              <input
                ref={fileRef}
                type="file"
                accept="application/pdf"
                className="file-input w-full"
                onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
                disabled={isSubmitting}
                required={!solicitud}
              />
              {selectedFile && (
                <div className="mt-2 flex items-center gap-2 text-sm text-success">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  {selectedFile.name}
                </div>
              )}
            </div>

            <div className="flex gap-3 justify-end pt-4 border-t border-base-300">
              <button type="button" className="btn btn-outline" onClick={resetCampos} disabled={isSubmitting}>
                Cancelar
              </button>
              <button type="submit" className="btn btn-info text-white gap-2" disabled={isSubmitting || !radicadoValido || !radicado}>
                {isUploading ? (
                  <><span className="loading loading-spinner loading-sm" />Subiendo...</>
                ) : isSubmitting ? (
                  <><span className="loading loading-spinner loading-sm" />Guardando...</>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    {solicitud ? "Actualizar Solicitud" : "Registrar Solicitud"}
                  </>
                )}
              </button>
            </div>
          </form>
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
