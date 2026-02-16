import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { apiCall, API_CONFIG } from "../../../../utils/api";

type ComunicacionData = {
  id: number;
  numerado: string;
  fecha_numerado: string;
  fecha_envio: string;
  fecha_creacion: string;
  url_documento?: string;
};

type Props = {
  isOpen: boolean;
  onClose: () => void;
  radicado: string;
  actoAdminId: number;
  idAuxiliar: number;
  tipoEtapa: string;
  editComunicacion?: ComunicacionData | null;
  onSuccess?: (comunicacionData: ComunicacionData) => void;
};

export default function ComunicacionModal({
  isOpen,
  onClose,
  radicado,
  actoAdminId,
  idAuxiliar: _idAuxiliar,
  tipoEtapa: _tipoEtapa,
  editComunicacion,
  onSuccess,
}: Props) {
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
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isEditing = !!editComunicacion;

  // Detectar el tema actual del documento
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
    }
  }, [isOpen, editComunicacion]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validar tipo de archivo
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
    // Solo permitir números y máximo 4 caracteres
    if (/^\d{0,4}$/.test(value)) {
      setNumerado(value);
      if (errors.numerado) {
        setErrors((prev) => ({ ...prev, numerado: "" }));
      }
    }
  };

  const handleFechaNumeradoChange = (
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    setFechaNumerado(e.target.value);
    if (errors.fecha_numerado) {
      setErrors((prev) => ({ ...prev, fecha_numerado: "" }));
    }
  };

  const handleFechaEnvioChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFechaEnvio(e.target.value);
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

    // Validar numerado
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

    // Validar fecha de numeración
    if (!fechaNumerado) {
      newErrors.fecha_numerado = "La fecha de numeración es requerida";
      isValid = false;
    }

    // Validar fecha de envío
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

    // Limpiar errores previos
    setErrors({
      numerado: "",
      fecha_numerado: "",
      fecha_envio: "",
      file: "",
      general: "",
    });

    // Validar formulario
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      // Crear FormData
      const formData = new FormData();
      formData.append("radicado", radicado);
      formData.append("acto_admin_id", actoAdminId.toString());
      formData.append("numerado", numerado);
      formData.append("fecha_numerado", fechaNumerado);
      formData.append("fecha_envio", fechaEnvio);

      // Agregar archivo si existe
      if (selectedFile) {
        formData.append("file", selectedFile);
      }

      // Determinar endpoint y método según si es creación o edición
      const endpoint = isEditing
        ? API_CONFIG.ENDPOINTS.FILE_COMUNICACION_UPDATE(editComunicacion!.id)
        : API_CONFIG.ENDPOINTS.FILE_COMUNICACION;

      const method = isEditing ? "PUT" : "POST";

      // Hacer la petición usando apiCall
      const res = await apiCall(endpoint, {
        method: method,
        body: formData,
      });

      if (res.ok) {
        // Éxito - Devolver los datos de la comunicación actualizada/creada
        const comunicacionData = res.data;

        if (onSuccess) {
          onSuccess(comunicacionData);
        }
        handleClose();
      } else {
        // Error del backend
        let errorMessage = "Error al guardar la comunicación";

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
      console.error("Error al guardar comunicación:", error);
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
              disabled={isSubmitting}
            />
            {errors.numerado && (
              <p className="text-error text-xs mt-1">{errors.numerado}</p>
            )}
          </div>

          {/* Fecha de Numeración */}
          <div>
            <label className="block text-sm font-medium text-base-content/70 mb-1">
              Fecha de Numeración <span className="text-error">*</span>
            </label>
            <input
              type="date"
              className={`input input-bordered w-full ${
                errors.fecha_numerado ? "input-error" : ""
              }`}
              value={fechaNumerado}
              onChange={handleFechaNumeradoChange}
              disabled={isSubmitting}
            />
            {errors.fecha_numerado && (
              <p className="text-error text-xs mt-1">{errors.fecha_numerado}</p>
            )}
          </div>

          {/* Fecha de Envío */}
          <div>
            <label className="block text-sm font-medium text-base-content/70 mb-1">
              Fecha de Envío <span className="text-error">*</span>
            </label>
            <input
              type="date"
              className={`input input-bordered w-full ${
                errors.fecha_envio ? "input-error" : ""
              }`}
              value={fechaEnvio}
              onChange={handleFechaEnvioChange}
              disabled={isSubmitting}
            />
            {errors.fecha_envio && (
              <p className="text-error text-xs mt-1">{errors.fecha_envio}</p>
            )}
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
