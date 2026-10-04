import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { apiCall, API_CONFIG, formatApiErrorDetail } from "../../../utils/api";
import {
  uploadFileToDocuments,
  generateDocumentFileName,
} from "../../../utils/fileUpload";
import CustomDateInput from "../Form/CustomDateInput";

type ComunicacionData = {
  id: number;
  numerado: string;
  fecha_numerado: string;
  fecha_envio: string;
  fecha_creacion: string;
  documento_comunicacion_id?: number;
};

type Props = {
  isOpen: boolean;
  onClose: () => void;
  expedienteId: number;
  actoAdminId: number;
  tipoEtapa: string;
  editComunicacion?: ComunicacionData | null;
  onSuccess?: (comunicacionData: ComunicacionData) => void;
  endpoints?: {
    create: string;
    update: (comunicacionId: number) => string;
  };
};

export default function ComunicacionModal({
  isOpen,
  onClose,
  expedienteId,
  actoAdminId,
  tipoEtapa: _tipoEtapa,
  editComunicacion,
  onSuccess,
  endpoints,
}: Props) {
  const comunicacionEndpoints = endpoints ?? {
    create: API_CONFIG.ENDPOINTS.FILE_COMUNICACION,
    update: API_CONFIG.ENDPOINTS.FILE_COMUNICACION_UPDATE,
  };
  const [numerado, setNumerado] = useState("");
  const [fechaNumerado, setFechaNumerado] = useState("");
  const [fechaEnvio, setFechaEnvio] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [theme, setTheme] = useState<string>("emerald");
  const [errors, setErrors] = useState({
    numerado: "",
    fecha_numerado: "",
    fecha_envio: "",
    file: "",
    general: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isEditing = !!editComunicacion;

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
      setErrors({
        numerado: "",
        fecha_numerado: "",
        fecha_envio: "",
        file: "",
        general: "",
      });
      if (editComunicacion) {
        setNumerado(String(editComunicacion.numerado).padStart(4, "0"));
        setFechaNumerado(editComunicacion.fecha_numerado);
        setFechaEnvio(editComunicacion.fecha_envio);
        setSelectedFile(null);
      } else {
        setNumerado("");
        setFechaNumerado("");
        setFechaEnvio("");
        setSelectedFile(null);
      }
      setIsSubmitting(false);
      setIsUploadingFile(false);
    }
  }, [isOpen, editComunicacion]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const validTypes = ["application/pdf", "image/jpeg", "image/png"];
      if (!validTypes.includes(file.type)) {
        setErrors((prev) => ({
          ...prev,
          file: "Solo se permiten archivos PDF, JPG o PNG",
        }));
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
        return;
      }

      // Validar tamaño (máximo 10MB)
      if (file.size > 10 * 1024 * 1024) {
        setErrors((prev) => ({
          ...prev,
          file: "El archivo no debe superar los 10MB",
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

  const handleNumeradoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    if (/^\d{0,4}$/.test(value)) {
      setNumerado(value);
      if (errors.numerado) {
        setErrors((prev) => ({ ...prev, numerado: "" }));
      }
    }
  };

  const handleFechaNumeradoChange = (value: string) => {
    setFechaNumerado(value);
    if (errors.fecha_numerado) {
      setErrors((prev) => ({ ...prev, fecha_numerado: "" }));
    }
  };

  const handleFechaEnvioChange = (value: string) => {
    setFechaEnvio(value);
    if (errors.fecha_envio) {
      setErrors((prev) => ({ ...prev, fecha_envio: "" }));
    }
  };

  const validateForm = () => {
    const newErrors = {
      numerado: "",
      fecha_numerado: "",
      fecha_envio: "",
      file: "",
      general: "",
    };

    let isValid = true;

    if (!numerado) {
      newErrors.numerado = "El numerado es requerido";
      isValid = false;
    } else if (numerado.length !== 4) {
      newErrors.numerado = "El numerado debe tener exactamente 4 dígitos";
      isValid = false;
    } else if (!/^\d{4}$/.test(numerado)) {
      newErrors.numerado = "El numerado debe contener solo números";
      isValid = false;
    }

    if (!fechaNumerado) {
      newErrors.fecha_numerado = "La fecha de numeración es requerida";
      isValid = false;
    }

    if (!fechaEnvio) {
      newErrors.fecha_envio = "La fecha de envío es requerida";
      isValid = false;
    }

    // Validar documento (solo requerido en creación, opcional en edición)
    if (!isEditing && !selectedFile) {
      newErrors.file = "Debe cargar un documento";
      isValid = false;
    }

    setErrors(newErrors);
    return isValid;
  };

  const handleSave = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    setErrors({
      numerado: "",
      fecha_numerado: "",
      fecha_envio: "",
      file: "",
      general: "",
    });

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      let documentoComunicacionId = editComunicacion?.documento_comunicacion_id;

      // Si llega nuevo archivo, primero subirlo a app-docs y esperar su file_id.
      if (selectedFile) {
        setIsUploadingFile(true);
        try {
          const fileName = generateDocumentFileName(
            "COM",
            numerado,
            fechaNumerado,
          );
          documentoComunicacionId = await uploadFileToDocuments(
            selectedFile,
            fileName,
          );
        } finally {
          setIsUploadingFile(false);
        }
      }

      if (!documentoComunicacionId) {
        throw new Error("No se pudo obtener el ID del documento");
      }

      const formData = new FormData();
      formData.append("expediente_id", expedienteId.toString());
      formData.append("acto_admin_id", actoAdminId.toString());
      formData.append("numerado", numerado);
      formData.append("fecha_numerado", fechaNumerado);
      formData.append("fecha_envio", fechaEnvio);
      formData.append(
        "documento_comunicacion_id",
        documentoComunicacionId.toString(),
      );

      const endpoint = isEditing
        ? comunicacionEndpoints.update(editComunicacion!.id)
        : comunicacionEndpoints.create;

      const method = isEditing ? "PUT" : "POST";

      const res = await apiCall(endpoint, {
        method: method,
        body: formData,
      });

      if (res.ok) {
        const comunicacionData = res.data;

        if (onSuccess) {
          onSuccess(comunicacionData);
        }
        handleClose();
      } else {
        const errorMessage = formatApiErrorDetail(
          res.detail,
          "Error al guardar la comunicación",
        );

        setErrors((prev) => ({
          ...prev,
          general: errorMessage,
        }));
      }
    } catch (error) {
      setErrors((prev) => ({
        ...prev,
        general: "Error de conexión al guardar la comunicación",
      }));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setNumerado("");
    setFechaNumerado("");
    setFechaEnvio("");
    setSelectedFile(null);
    setErrors({
      numerado: "",
      fecha_numerado: "",
      fecha_envio: "",
      file: "",
      general: "",
    });
    setIsSubmitting(false);
    setIsUploadingFile(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    onClose();
  };

  if (!isOpen) return null;

  const modalContent = (
    <div
      data-theme={theme}
      className="fixed inset-0 z-[999999] flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={handleClose}
    >
      <div
        className="bg-base-100 rounded-lg p-6 w-full max-w-xl mx-4 shadow-2xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="font-bold text-lg mb-4 text-base-content">
          {isEditing ? "Editar Comunicación" : "Nueva Comunicación"}
        </h3>

        <form onSubmit={handleSave} className="space-y-4 select-none">
          {/* Numerado */}
          <div>
            <label className="block text-sm font-medium text-base-content/70 mb-1">
              Numerado <span className="text-error">*</span>
              <span className="text-xs text-base-content/50 ml-2">
                (4 dígitos)
              </span>
            </label>
            <input
              type="text"
              className={`input input-bordered w-full font-mono ${
                errors.numerado ? "input-error" : ""
              }`}
              placeholder="0001"
              value={numerado}
              onChange={handleNumeradoChange}
              maxLength={4}
              disabled={isSubmitting || isUploadingFile}
            />
            {errors.numerado && (
              <p className="text-error text-xs mt-1">{errors.numerado}</p>
            )}
          </div>

          {/* Fecha de Numeración y Fecha de Envío */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-base-content/70 mb-1">
                Fecha de Numeración <span className="text-error">*</span>
              </label>
              <CustomDateInput
                error={!!errors.fecha_numerado}
                value={fechaNumerado}
                onChange={handleFechaNumeradoChange}
                max={new Date().toISOString().split('T')[0]}
                disabled={isSubmitting || isUploadingFile}
              />
              {errors.fecha_numerado && (
                <p className="text-error text-xs mt-1">{errors.fecha_numerado}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-base-content/70 mb-1">
                Fecha de Envío <span className="text-error">*</span>
              </label>
              <CustomDateInput
                error={!!errors.fecha_envio}
                value={fechaEnvio}
                onChange={handleFechaEnvioChange}
                max={new Date().toISOString().split('T')[0]}
                disabled={isSubmitting || isUploadingFile}
              />
              {errors.fecha_envio && (
                <p className="text-error text-xs mt-1">{errors.fecha_envio}</p>
              )}
            </div>
          </div>

          {/* Archivo */}
          <div>
            <label className="block text-sm font-medium text-base-content/70 mb-1">
              Documento {!isEditing && <span className="text-error">*</span>}
              {isEditing && (
                <span className="text-xs text-base-content/50 ml-2">
                  (Opcional - Solo si desea reemplazar)
                </span>
              )}
              <span className="text-xs text-base-content/50 ml-2">
                (PDF, JPG, PNG - Máx. 10MB)
              </span>
            </label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.jpg,.jpeg,.png,image/jpeg,image/png,application/pdf"
              className={`file-input file-input-bordered w-full ${
                errors.file ? "file-input-error" : ""
              }`}
              onChange={handleFileChange}
              disabled={isSubmitting || isUploadingFile}
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
            {isEditing && !selectedFile && !errors.file && (
              <p className="mt-2 text-xs text-base-content/60">
                Archivo actual: Documento registrado
              </p>
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
          <div className="flex justify-end space-x-2 mt-6">
            <button
              type="button"
              onClick={handleClose}
              className="btn btn-ghost"
              disabled={isSubmitting || isUploadingFile}
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="btn btn-success text-white"
              disabled={isSubmitting || isUploadingFile}
            >
              {isUploadingFile ? (
                <>
                  <span className="loading loading-spinner loading-sm"></span>
                  Subiendo archivo...
                </>
              ) : isSubmitting ? (
                <>
                  <span className="loading loading-spinner loading-sm"></span>
                  Guardando...
                </>
              ) : isEditing ? (
                "Actualizar"
              ) : (
                "Agregar"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
