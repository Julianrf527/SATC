import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { API_CONFIG, apiCall } from "../../../utils/api";
import { X, Upload } from "lucide-react";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  documentoId: number;
  onSuccess: () => void;
};

export default function SubirVersionModal({
  isOpen,
  onClose,
  documentoId,
  onSuccess,
}: Props) {
  const [comentario, setComentario] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [theme, setTheme] = useState<string>("emerald");
  const [errors, setErrors] = useState({
    file: "",
    general: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Detectar tema
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

  // Reset form
  useEffect(() => {
    if (isOpen) {
      setComentario("");
      setSelectedFile(null);
      setErrors({
        file: "",
        general: "",
      });
      setIsSubmitting(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }, [isOpen]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validar tipos permitidos
      const validTypes = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
      ];

      if (!validTypes.includes(file.type)) {
        setErrors((prev) => ({
          ...prev,
          file: "Solo se permiten archivos PDF, DOCX o DOC",
        }));
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
        return;
      }

      // Validar tamaño (máximo 15MB)
      if (file.size > 15 * 1024 * 1024) {
        setErrors((prev) => ({
          ...prev,
          file: "El archivo no debe superar los 15MB",
        }));
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
        return;
      }

      setSelectedFile(file);
      if (errors.file) {
        setErrors((prev) => ({ ...prev, file: "" }));
      }
    }
  };

  const validateForm = () => {
    const newErrors = {
      file: "",
      general: "",
    };

    let isValid = true;

    if (!selectedFile) {
      newErrors.file = "Debe seleccionar un archivo";
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
      if (comentario.trim()) {
        formData.append("comentario", comentario.trim());
      }
      formData.append("archivo", selectedFile!);

      const res = await apiCall(
        API_CONFIG.ENDPOINTS.DOCS_UPLOAD_VERSION(documentoId),
        {
          method: "POST",
          body: formData,
        }
      );

      if (res.ok) {
        onSuccess();
        handleClose();
      } else {
        let errorMessage = "Error al subir la nueva versión";

        if (res.detail) {
          if (typeof res.detail === "string") {
            errorMessage = res.detail;
          } else if (Array.isArray(res.detail)) {
            errorMessage = res.detail.map((err: any) => err.msg).join(", ");
          }
        }

        setErrors((prev) => ({
          ...prev,
          general: errorMessage,
        }));
      }
    } catch (error) {
      /* console.error("Error al subir versión:", error); */
      setErrors((prev) => ({
        ...prev,
        general: "Error de conexión al subir la versión",
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
            <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
              <Upload className="text-primary" size={20} />
            </div>
            <div>
              <h3 className="font-bold text-lg text-base-content">
                Subir Nueva Versión
              </h3>
              <p className="text-xs text-base-content/60">
                Cargue el documento corregido
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
        <div className="p-6 space-y-4 select-none">
          {/* Comentario */}
          <div>
            <label className="block text-sm font-medium text-base-content/70 mb-1">
              Comentario sobre los cambios
              <span className="text-base-content/50 text-xs ml-2">
                (Opcional)
              </span>
            </label>
            <textarea
              className="textarea textarea-bordered w-full h-24"
              placeholder="Describa brevemente los cambios realizados..."
              value={comentario}
              onChange={(e) => setComentario(e.target.value)}
              disabled={isSubmitting}
            />
          </div>

          {/* Archivo */}
          <div>
            <label className="block text-sm font-medium text-base-content/70 mb-1">
              Archivo <span className="text-error">*</span>
              <span className="text-xs text-base-content/50 ml-2">
                (PDF, DOCX, DOC - Máx. 15MB)
              </span>
            </label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.doc,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/msword"
              className={`file-input file-input-bordered w-full ${
                errors.file ? "file-input-error" : ""
              }`}
              onChange={handleFileChange}
              disabled={isSubmitting}
            />
            {errors.file && (
              <p className="text-error text-xs mt-1">{errors.file}</p>
            )}
            {selectedFile && !errors.file && (
              <div className="mt-2 flex items-center gap-2 text-sm text-success">
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
                <span>{selectedFile.name}</span>
              </div>
            )}
          </div>

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
              className="btn btn-primary"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <span className="loading loading-spinner loading-sm"></span>
                  Subiendo...
                </>
              ) : (
                <>
                  <Upload size={18} />
                  Subir Versión
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
