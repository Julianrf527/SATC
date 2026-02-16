import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";

type DocumentoData = {
  id: number;
  nombre: string;
  url_documento: string;
  fecha_subida: string;
};

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onSave: (formData: FormData) => Promise<{ ok: boolean; error?: string }>;
  editDocumento: DocumentoData | null;
  tiposDocumento: string[];
};

export default function DocumentModal({
  isOpen,
  onClose,
  onSave,
  editDocumento,
  tiposDocumento,
}: Props) {
  const [tipoDocumento, setTipoDocumento] = useState("");
  const [nombrePersonalizado, setNombrePersonalizado] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [theme, setTheme] = useState<string>("emerald");
  const [errors, setErrors] = useState({
    tipo: "",
    nombre: "",
    file: "",
    general: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isEditing = !!editDocumento;
  const isOtroSelected = tipoDocumento === "Otro";

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

  // Cargar datos cuando se abre el modal
  useEffect(() => {
    if (isOpen) {
      setErrors({
        tipo: "",
        nombre: "",
        file: "",
        general: "",
      });

      if (editDocumento) {
        // Verificar si el nombre está en los tipos predefinidos
        const esTipoPredefinido = tiposDocumento.includes(editDocumento.nombre);

        if (esTipoPredefinido) {
          setTipoDocumento(editDocumento.nombre);
          setNombrePersonalizado("");
        } else {
          setTipoDocumento("Otro");
          setNombrePersonalizado(editDocumento.nombre);
        }
        setSelectedFile(null);
      } else {
        // Reset para nuevo registro
        setTipoDocumento("");
        setNombrePersonalizado("");
        setSelectedFile(null);
      }
      setIsSubmitting(false);
    }
  }, [isOpen, editDocumento, tiposDocumento]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type !== "application/pdf") {
        setErrors((prev) => ({
          ...prev,
          file: "Solo se permiten archivos PDF",
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

  const handleTipoChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setTipoDocumento(e.target.value);
    if (errors.tipo) {
      setErrors((prev) => ({ ...prev, tipo: "" }));
    }
    // Limpiar nombre personalizado si no es "Otro"
    if (e.target.value !== "Otro") {
      setNombrePersonalizado("");
      if (errors.nombre) {
        setErrors((prev) => ({ ...prev, nombre: "" }));
      }
    }
  };

  const handleNombrePersonalizadoChange = (
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const valor = e.target.value;
    setNombrePersonalizado(valor);

    // Validación en tiempo real
    if (valor.trim()) {
      const nombreNormalizado = valor.trim().toLowerCase();

      // Validar si existe en los tipos predefinidos
      const existeEnTipos = tiposDocumento.some(
        (tipo) => tipo.toLowerCase() === nombreNormalizado,
      );

      if (existeEnTipos) {
        setErrors((prev) => ({
          ...prev,
          nombre:
            "Este nombre ya existe en los tipos de documento. Use el selector.",
        }));
      } else if (errors.nombre) {
        setErrors((prev) => ({ ...prev, nombre: "" }));
      }
    } else if (
      errors.nombre &&
      errors.nombre !== "Debe ingresar un nombre para el documento"
    ) {
      setErrors((prev) => ({ ...prev, nombre: "" }));
    }
  };

  const validateForm = () => {
    const newErrors = {
      tipo: "",
      nombre: "",
      file: "",
      general: "",
    };

    let isValid = true;

    // Validar tipo de documento
    if (!tipoDocumento) {
      newErrors.tipo = "Debe seleccionar un tipo de documento";
      isValid = false;
    }

    // Validar nombre personalizado si seleccionó "Otro"
    if (isOtroSelected) {
      if (!nombrePersonalizado.trim()) {
        newErrors.nombre = "Debe ingresar un nombre para el documento";
        isValid = false;
      } else {
        const nombreNormalizado = nombrePersonalizado.trim().toLowerCase();

        // Validar que el nombre no exista en los tipos predefinidos
        const existeEnTipos = tiposDocumento.some(
          (tipo) => tipo.toLowerCase() === nombreNormalizado,
        );

        if (existeEnTipos) {
          newErrors.nombre =
            "Este nombre ya existe en los tipos de documento. Use el selector.";
          isValid = false;
        }
      }
    }

    // Validar archivo PDF (obligatorio si es nuevo)
    if (!isEditing && !selectedFile) {
      newErrors.file = "Debe seleccionar un archivo PDF";
      isValid = false;
    }

    setErrors(newErrors);
    return isValid;
  };

  const handleSave = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    // Limpiar errores previos
    setErrors({
      tipo: "",
      nombre: "",
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

      // El nombre final del documento
      const nombreFinal = isOtroSelected
        ? nombrePersonalizado.trim()
        : tipoDocumento;
      formData.append("nombre", nombreFinal);

      if (selectedFile) {
        formData.append("file", selectedFile);
      }

      const result = await onSave(formData);

      if (result.ok) {
        handleClose();
      } else {
        // Mostrar error del backend
        setErrors((prev) => ({
          ...prev,
          general: result.error || "Error al guardar el documento",
        }));
      }
    } catch (error) {
      setErrors((prev) => ({
        ...prev,
        general: "Error inesperado al guardar el documento",
      }));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setTipoDocumento("");
    setNombrePersonalizado("");
    setSelectedFile(null);
    setErrors({
      tipo: "",
      nombre: "",
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
        className="bg-base-100 rounded-lg p-6 w-full max-w-lg mx-4 shadow-2xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="font-bold text-lg mb-4 text-base-content">
          {isEditing ? "Editar Documento" : "Nuevo Documento"}
        </h3>

        <form onSubmit={handleSave} className="space-y-4 select-none">
          {/* Tipo de Documento */}
          <div>
            <label className="block text-sm font-medium text-base-content/70 mb-1">
              Tipo de Documento <span className="text-error">*</span>
            </label>
            <select
              className={`select select-bordered w-full ${
                errors.tipo ? "select-error" : ""
              }`}
              value={tipoDocumento}
              onChange={handleTipoChange}
              disabled={isSubmitting}
            >
              <option value="">Seleccione un tipo</option>
              {tiposDocumento.map((tipo) => (
                <option key={tipo} value={tipo}>
                  {tipo}
                </option>
              ))}
              <option value="Otro">Otro</option>
            </select>
            {errors.tipo && (
              <p className="text-error text-xs mt-1">{errors.tipo}</p>
            )}
          </div>

          {/* Nombre Personalizado (solo si es "Otro") */}
          {isOtroSelected && (
            <div>
              <label className="block text-sm font-medium text-base-content/70 mb-1">
                Nombre del Documento <span className="text-error">*</span>
              </label>
              <input
                type="text"
                className={`input input-bordered w-full ${
                  errors.nombre ? "input-error" : ""
                }`}
                placeholder="Ingrese un nombre diferente a los tipos existentes"
                value={nombrePersonalizado}
                onChange={handleNombrePersonalizadoChange}
                disabled={isSubmitting}
              />
              {errors.nombre && (
                <p className="text-error text-xs mt-1">{errors.nombre}</p>
              )}
              {!errors.nombre && isOtroSelected && (
                <p className="text-xs text-base-content/50 mt-1">
                  El nombre debe ser diferente a: {tiposDocumento.join(", ")}
                </p>
              )}
            </div>
          )}

          {/* Archivo PDF */}
          <div>
            <label className="block text-sm font-medium text-base-content/70 mb-1">
              Documento PDF{" "}
              {!isEditing && <span className="text-error">*</span>}
              {isEditing && (
                <span className="text-xs text-base-content/50 ml-2">
                  (Opcional - Solo si desea reemplazar)
                </span>
              )}
            </label>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
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
                "Crear"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
