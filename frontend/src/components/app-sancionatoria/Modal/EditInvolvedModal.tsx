import { useState, useEffect } from "react";
import { createPortal } from "react-dom";

type Involved = {
  id: number;
  numero_documento: number;
  digito_verificacion: string | null;
  tipo_documento: string;
  nombre: string;
  celular: number;
  correo: string;
};

type Props = {
  involved: Involved | null;
  onClose: () => void;
  onSave: (
    id: number,
    data: {
      nombre: string;
      celular: string;
      correo: string;
      digito_verificacion: string;
    }
  ) => Promise<void>;
};

export default function EditInvolvedModal({
  involved,
  onClose,
  onSave,
}: Props) {
  const [nombre, setNombre] = useState("");
  const [celular, setCelular] = useState("");
  const [correo, setCorreo] = useState("");
  const [theme, setTheme] = useState<string>("emerald");
  const [errorGeneral, setErrorGeneral] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<{
    nombre?: string;
    celular?: string;
    correo?: string;
    digitoVerificacion?: string;
  }>({});

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

  // Cargar datos cuando se abre el modal
  useEffect(() => {
    if (involved) {
      setNombre(involved.nombre);
      setCelular(String(involved.celular));
      setCorreo(involved.correo);
      setErrors({});
      setErrorGeneral("");
      setIsSubmitting(false);
    }
  }, [involved]);

  const validate = (): boolean => {
    const newErrors: typeof errors = {};

    if (!nombre.trim()) {
      newErrors.nombre = "El nombre es requerido";
    } else if (nombre.length > 100) {
      newErrors.nombre = "El nombre no puede exceder 100 caracteres";
    }

    if (!celular.trim()) {
      newErrors.celular = "El celular es requerido";
    } else if (!/^\d+$/.test(celular)) {
      newErrors.celular = "El celular debe contener solo números";
    } else if (celular.length < 7 || celular.length > 15) {
      newErrors.celular = "El celular debe tener entre 7 y 15 dígitos";
    }

    if (!correo.trim()) {
      newErrors.correo = "El correo es requerido";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(correo)) {
      newErrors.correo = "Correo inválido";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorGeneral("");

    if (!involved || !validate()) return;

    setIsSubmitting(true);
    try {
      await onSave(involved.id, {
        nombre: nombre.trim(),
        celular: celular.trim(),
        correo: correo.trim().toLowerCase(),
        digito_verificacion: involved.digito_verificacion || "",
      });
      handleClose();
    } catch (error) {
      /* console.error("Error guardando:", error); */
      setErrorGeneral("Error al actualizar el involucrado");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setNombre("");
    setCelular("");
    setCorreo("");
    setErrors({});
    setErrorGeneral("");
    setIsSubmitting(false);
    onClose();
  };

  if (!involved) return null;

  const modalContent = (
    <div
      data-theme={theme}
      className="fixed inset-0 z-[999999] flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={handleClose}
    >
      <div
        className="bg-base-100 rounded-lg p-6 w-full max-w-2xl mx-4 shadow-2xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="font-bold text-lg mb-4 text-base-content">
          Editar Involucrado
        </h3>

        {errorGeneral && (
          <div className="alert alert-error mb-4">
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
            <span>{errorGeneral}</span>
          </div>
        )}

        {/* Info del documento (no editable) */}
        <div className="bg-base-200 p-4 rounded-lg mb-4">
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="font-semibold">Tipo:</span>{" "}
              {involved.tipo_documento}
            </div>
            <div>
              <span className="font-semibold">Número:</span>{" "}
              {involved.numero_documento}
            </div>
            {involved.tipo_documento === "NIT" &&
              involved.digito_verificacion && (
                <div>
                  <span className="font-semibold">DV:</span>{" "}
                  {involved.digito_verificacion}
                </div>
              )}
          </div>
          <div className="text-xs text-base-content/70 mt-2">
            * El tipo, número de documento y dígito de verificación no se pueden
            modificar
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 select-none">
          {/* Nombre */}
          <div>
            <label className="block text-sm font-medium text-base-content/70 mb-1">
              Nombre <span className="text-error">*</span>
            </label>
            <input
              type="text"
              className={`input input-bordered w-full ${
                errors.nombre ? "input-error" : ""
              }`}
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              maxLength={100}
              disabled={isSubmitting}
            />
            {errors.nombre && (
              <label className="label">
                <span className="label-text-alt text-error">
                  {errors.nombre}
                </span>
              </label>
            )}
          </div>

          {/* Celular */}
          <div>
            <label className="block text-sm font-medium text-base-content/70 mb-1">
              Celular <span className="text-error">*</span>
            </label>
            <input
              type="text"
              className={`input input-bordered w-full ${
                errors.celular ? "input-error" : ""
              }`}
              value={celular}
              onChange={(e) => setCelular(e.target.value)}
              maxLength={15}
              disabled={isSubmitting}
            />
            {errors.celular && (
              <label className="label">
                <span className="label-text-alt text-error">
                  {errors.celular}
                </span>
              </label>
            )}
          </div>

          {/* Correo */}
          <div>
            <label className="block text-sm font-medium text-base-content/70 mb-1">
              Correo <span className="text-error">*</span>
            </label>
            <input
              type="email"
              className={`input input-bordered w-full ${
                errors.correo ? "input-error" : ""
              }`}
              value={correo}
              onChange={(e) => setCorreo(e.target.value)}
              disabled={isSubmitting}
            />
            {errors.correo && (
              <label className="label">
                <span className="label-text-alt text-error">
                  {errors.correo}
                </span>
              </label>
            )}
          </div>

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
              ) : (
                "Guardar Cambios"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
