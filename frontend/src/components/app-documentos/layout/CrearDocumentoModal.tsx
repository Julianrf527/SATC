import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { API_CONFIG, apiCall } from "../../../utils/api";
import { X, Upload, FileText } from "lucide-react";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  revisores: Usuario[];
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

type Usuario = {
  id: number;
  nombre_completo: string;
  email: string;
};

export default function CrearDocumentoModal({
  isOpen,
  onClose,
  onSuccess,
  revisores,
  setToast,
}: Props) {
  const [nombre, setNombre] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [tipoArchivo, setTipoArchivo] = useState<"pdf" | "docx" | "doc" | null>(
    null
  );
  const [revisoresIds, setRevisoresIds] = useState<number[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [theme, setTheme] = useState<string>("emerald");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const formRef = useRef<HTMLFormElement>(null);

  // Detectar tema actual
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

  // Reset form cuando se abre el modal
  useEffect(() => {
    if (isOpen) {
      setNombre("");
      setDescripcion("");
      setTipoArchivo(null);
      setRevisoresIds([]);
      setSelectedFile(null);
      setIsSubmitting(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }, [isOpen]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Verificar tamaño
      if (file.size > 10 * 1024 * 1024) {
        setToast({
          id: Date.now(),
          message: "El archivo no debe superar los 10MB",
          type: "error",
        });
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
        return;
      }

      // Detectar tipo de archivo automáticamente
      let detectedType: "pdf" | "docx" | "doc" | null = null;
      const fileName = file.name.toLowerCase();

      if (file.type === "application/pdf" || fileName.endsWith(".pdf")) {
        detectedType = "pdf";
      } else if (
        file.type ===
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ||
        fileName.endsWith(".docx")
      ) {
        detectedType = "docx";
      } else if (
        file.type === "application/msword" ||
        fileName.endsWith(".doc")
      ) {
        detectedType = "doc";
      }

      if (!detectedType) {
        setToast({
          id: Date.now(),
          message: "Tipo de archivo no válido. Solo se aceptan PDF, DOC o DOCX",
          type: "error",
        });
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
        return;
      }

      setTipoArchivo(detectedType);
      setSelectedFile(file);
      setToast({
        id: Date.now(),
        message: `Archivo ${detectedType.toUpperCase()} detectado correctamente`,
        type: "success",
      });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedFile || !tipoArchivo) {
      setToast({
        id: Date.now(),
        message: "Debe seleccionar un archivo válido",
        type: "error",
      });
      return;
    }

    if (revisoresIds.length === 0) {
      setToast({
        id: Date.now(),
        message: "Debe seleccionar al menos un revisor",
        type: "error",
      });
      return;
    }

    setIsSubmitting(true);

    try {
      const formData = new FormData();
      formData.append("nombre", nombre.trim());

      if (descripcion.trim()) {
        formData.append("descripcion", descripcion.trim());
      }

      formData.append("tipo_archivo", tipoArchivo);
      formData.append("revisores_ids", JSON.stringify(revisoresIds));
      formData.append("archivo", selectedFile!);

      const res = await apiCall(API_CONFIG.ENDPOINTS.DOCS_CREATE, {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        setToast({
          id: Date.now(),
          message: "Documento creado exitosamente",
          type: "success",
        });
        onSuccess();
        onClose();
      } else {
        let errorMessage = "Error al crear el documento";

        if (res.detail) {
          if (typeof res.detail === "string") {
            errorMessage = res.detail;
          } else if (Array.isArray(res.detail)) {
            errorMessage = res.detail.map((err: any) => err.msg).join(", ");
          }
        }

        setToast({
          id: Date.now(),
          message: errorMessage,
          type: "error",
        });
      }
    } catch (error) {
      /* console.error("Error al crear documento:", error); */
      setToast({
        id: Date.now(),
        message: "Error de conexión al crear el documento",
        type: "error",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  const modalContent = (
    <div
      data-theme={theme}
      className="fixed inset-0 z-[999999] flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-base-100 rounded-lg w-full max-w-2xl mx-4 shadow-2xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-base-100 border-b border-base-300 px-6 py-4 flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
              <FileText className="text-success" size={20} />
            </div>
            <div>
              <h3 className="font-bold text-lg text-base-content">
                Crear Nuevo Documento
              </h3>
              <p className="text-xs text-base-content/60">
                Complete la información del documento
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="btn btn-ghost btn-sm btn-circle"
            disabled={isSubmitting}
            type="button"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body - FORM */}
        <form
          ref={formRef}
          onSubmit={handleSubmit}
          className="p-6 space-y-5 select-none"
        >
          {/* Nombre */}
          <div>
            <label className="block text-sm font-medium text-base-content/70 mb-1">
              Nombre del Documento <span className="text-error">*</span>
            </label>
            <input
              type="text"
              className="input input-bordered w-full"
              placeholder="Ej: Contrato de Servicios 2024"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              disabled={isSubmitting}
              required
            />
          </div>

          {/* Descripción */}
          <div>
            <label className="block text-sm font-medium text-base-content/70 mb-1">
              Descripción{" "}
              <span className="text-base-content/50 text-xs">(Opcional)</span>
            </label>
            <textarea
              className="textarea textarea-bordered w-full h-20"
              placeholder="Descripción breve del documento..."
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
              disabled={isSubmitting}
            />
          </div>

          {/* Archivo */}
          <div>
            <label className="block text-sm font-medium text-base-content/70 mb-1">
              Archivo <span className="text-error">*</span>
              <span className="text-xs text-base-content/50 ml-2">
                (PDF, DOC o DOCX - Máx. 10MB)
              </span>
            </label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              className="file-input file-input-bordered w-full"
              onChange={handleFileChange}
              disabled={isSubmitting}
              required
            />
            {selectedFile && tipoArchivo && (
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
                <span className="badge badge-success badge-sm">
                  {tipoArchivo.toUpperCase()}
                </span>
              </div>
            )}
          </div>

          {/* Revisores - CHIPS SELECCIONABLES */}
          <div>
            <label className="block text-sm font-medium text-base-content/70 mb-2">
              Asignar Revisores <span className="text-error">*</span>
              <span className="text-xs text-base-content/50 ml-2">
                (Click para seleccionar/deseleccionar)
              </span>
            </label>

            <div className="border border-base-300 rounded-lg p-3 bg-base-100 max-h-48 overflow-y-auto space-y-2">
              {revisores.length === 0 ? (
                <p className="text-sm text-base-content/50 text-center py-2">
                  No hay revisores disponibles
                </p>
              ) : (
                revisores.map((revisor) => {
                  const isSelected = revisoresIds.includes(revisor.id);
                  return (
                    <button
                      key={revisor.id}
                      type="button"
                      onClick={() => {
                        setRevisoresIds((prev) =>
                          prev.includes(revisor.id)
                            ? prev.filter((id) => id !== revisor.id)
                            : [...prev, revisor.id]
                        );
                      }}
                      disabled={isSubmitting}
                      className={`w-full text-left px-4 py-3 rounded-lg border-2 transition-all duration-200 ${
                        isSelected
                          ? "border-success bg-success/10 shadow-sm"
                          : "border-base-300 hover:border-base-400 bg-base-100"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                            isSelected
                              ? "border-success bg-success"
                              : "border-base-300"
                          }`}
                        >
                          {isSelected && (
                            <svg
                              className="w-3 h-3 text-white"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={3}
                                d="M5 13l4 4L19 7"
                              />
                            </svg>
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p
                            className={`text-sm font-medium truncate ${
                              isSelected ? "text-success" : "text-base-content"
                            }`}
                          >
                            {revisor.nombre_completo}
                          </p>
                          <p className="text-xs text-base-content/60 truncate">
                            {revisor.email}
                          </p>
                        </div>
                      </div>
                    </button>
                  );
                })
              )}
            </div>

            {revisoresIds.length > 0 && (
              <div className="mt-2 flex items-center gap-2">
                <div className="badge badge-success gap-1">
                  <svg
                    className="w-3 h-3"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  {revisoresIds.length} seleccionado
                  {revisoresIds.length > 1 ? "s" : ""}
                </div>
              </div>
            )}
          </div>

          {/* Botones */}
          <div className="flex justify-end space-x-2 pt-4 border-t border-base-300">
            <button
              type="button"
              onClick={onClose}
              className="btn btn-ghost"
              disabled={isSubmitting}
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="btn btn-success text-white"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <span className="loading loading-spinner loading-sm"></span>
                  Creando...
                </>
              ) : (
                <>
                  <Upload size={18} />
                  Crear Documento
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
