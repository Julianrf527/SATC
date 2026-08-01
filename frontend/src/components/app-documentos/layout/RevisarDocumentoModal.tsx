import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { API_CONFIG, apiCall, formatApiErrorDetail } from "../../../utils/api";
import { X, CheckCircle, XCircle, Eye } from "lucide-react";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  documentoId: number;
  nombreDocumento: string;
  onSuccess: () => void;
};

export default function RevisarDocumentoModal({
  isOpen,
  onClose,
  documentoId,
  nombreDocumento,
  onSuccess,
}: Props) {
  const [estadoRevision, setEstadoRevision] = useState<"aprobado" | "devuelto">(
    "aprobado",
  );
  const [comentarios, setComentarios] = useState("");
  const [theme, setTheme] = useState<string>("emerald");
  const [errors, setErrors] = useState({
    comentarios: "",
    general: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const updateTheme = () => {
      const currentTheme =
        document.querySelector("[data-theme]")?.getAttribute("data-theme") ||
        "emerald";
      setTheme(currentTheme);
    };

    updateTheme();

    const observer = new MutationObserver(updateTheme);
    const targetNode = document.querySelector("[data-theme]");

    if (targetNode) {
      observer.observe(targetNode, {
        attributes: true,
        attributeFilter: ["data-theme"],
      });
    }

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (isOpen) {
      setEstadoRevision("aprobado");
      setComentarios("");
      setErrors({
        comentarios: "",
        general: "",
      });
      setIsSubmitting(false);
    }
  }, [isOpen]);

  const validateForm = () => {
    const newErrors = {
      comentarios: "",
      general: "",
    };

    let isValid = true;

    // Los comentarios son obligatorios si se devuelve
    if (estadoRevision === "devuelto" && !comentarios.trim()) {
      newErrors.comentarios = "Debe especificar el motivo de la devolución";
      isValid = false;
    }

    setErrors(newErrors);
    return isValid;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      const formData = new FormData();
      // No enviamos revisor_id, el backend usa el usuario autenticado del token
      formData.append("estado_revision", estadoRevision);
      if (comentarios.trim()) {
        formData.append("comentarios", comentarios.trim());
      }

      const res = await apiCall(API_CONFIG.ENDPOINTS.DOCS_REVIEW(documentoId), {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        onSuccess();
        handleClose();
      } else {
        const errorMessage = formatApiErrorDetail(
          res.detail,
          "Error al registrar la revisión",
        );

        setErrors((prev) => ({
          ...prev,
          general: errorMessage,
        }));
      }
    } catch (error) {
      setErrors((prev) => ({
        ...prev,
        general: "Error de conexión al revisar el documento",
      }));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    onClose();
  };

  if (!isOpen) return null;

  const modalContent = (
    <div
      data-theme={theme}
      className="fixed inset-0 z-[9999999] flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={handleClose}
    >
      <div
        className="bg-base-100 rounded-lg w-full max-w-xl mx-4 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-base-100 border-b border-base-300 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
              <Eye className="text-success" size={20} />
            </div>
            <div>
              <h3 className="font-bold text-lg text-base-content">
                Revisar Documento
              </h3>
              <p className="text-xs text-base-content/60 truncate max-w-md">
                {nombreDocumento}
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="btn btn-ghost btn-sm btn-circle"
            disabled={isSubmitting}
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5 select-none">
          {/* Decisión */}
          <div>
            <label className="block text-sm font-medium text-base-content/70 mb-3">
              Decisión <span className="text-error">*</span>
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => {
                  setEstadoRevision("aprobado");
                  if (errors.comentarios) {
                    setErrors((prev) => ({ ...prev, comentarios: "" }));
                  }
                }}
                className={`p-4 rounded-lg border-2 transition-all ${
                  estadoRevision === "aprobado"
                    ? "border-green-500 bg-green-500/10"
                    : "border-base-300 hover:border-green-500/50"
                }`}
                disabled={isSubmitting}
              >
                <div className="flex flex-col items-center gap-2">
                  <CheckCircle
                    className={
                      estadoRevision === "aprobado"
                        ? "text-green-600"
                        : "text-base-content/40"
                    }
                    size={32}
                  />
                  <span
                    className={`font-semibold ${
                      estadoRevision === "aprobado"
                        ? "text-green-600"
                        : "text-base-content/60"
                    }`}
                  >
                    Aprobar
                  </span>
                  <span className="text-xs text-base-content/50 text-center">
                    El documento cumple con los requisitos
                  </span>
                </div>
              </button>

              <button
                onClick={() => setEstadoRevision("devuelto")}
                className={`p-4 rounded-lg border-2 transition-all ${
                  estadoRevision === "devuelto"
                    ? "border-red-500 bg-red-500/10"
                    : "border-base-300 hover:border-red-500/50"
                }`}
                disabled={isSubmitting}
              >
                <div className="flex flex-col items-center gap-2">
                  <XCircle
                    className={
                      estadoRevision === "devuelto"
                        ? "text-red-600"
                        : "text-base-content/40"
                    }
                    size={32}
                  />
                  <span
                    className={`font-semibold ${
                      estadoRevision === "devuelto"
                        ? "text-red-600"
                        : "text-base-content/60"
                    }`}
                  >
                    Devolver
                  </span>
                  <span className="text-xs text-base-content/50 text-center">
                    Requiere correcciones o ajustes
                  </span>
                </div>
              </button>
            </div>
          </div>

          {/* Comentarios */}
          <div>
            <label className="block text-sm font-medium text-base-content/70 mb-1">
              Comentarios
              {estadoRevision === "devuelto" ? (
                <span className="text-error"> *</span>
              ) : (
                <span className="text-base-content/50 text-xs ml-2">
                  (Opcional)
                </span>
              )}
            </label>
            <textarea
              className={`textarea textarea-bordered w-full h-32 ${
                errors.comentarios ? "textarea-error" : ""
              }`}
              placeholder={
                estadoRevision === "devuelto"
                  ? "Especifique las correcciones necesarias..."
                  : "Agregue comentarios adicionales si lo desea..."
              }
              value={comentarios}
              onChange={(e) => {
                setComentarios(e.target.value);
                if (errors.comentarios) {
                  setErrors((prev) => ({ ...prev, comentarios: "" }));
                }
              }}
              disabled={isSubmitting}
            />
            {errors.comentarios && (
              <p className="text-error text-xs mt-1">{errors.comentarios}</p>
            )}
          </div>

          {/* Advertencia si es devolución */}
          {estadoRevision === "devuelto" && (
            <div className="alert alert-warning">
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
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
              <span className="text-sm">
                Al devolver el documento, el creador deberá realizar las
                correcciones. Después de 3 devoluciones, el proceso se
                finalizará automáticamente.
              </span>
            </div>
          )}

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
              onClick={handleClose}
              className="btn btn-ghost"
              disabled={isSubmitting}
            >
              Cancelar
            </button>
            <button
              onClick={handleSubmit}
              className={`btn ${
                estadoRevision === "aprobado" ? "btn-success" : "btn-error"
              } text-white`}
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <span className="loading loading-spinner loading-sm"></span>
                  Procesando...
                </>
              ) : (
                <>
                  {estadoRevision === "aprobado" ? (
                    <>
                      <CheckCircle size={18} />
                      Aprobar Documento
                    </>
                  ) : (
                    <>
                      <XCircle size={18} />
                      Devolver Documento
                    </>
                  )}
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
