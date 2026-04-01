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
    data: { nombre: string; celular: string; correo: string; digito_verificacion: string }
  ) => Promise<void>;
};

export default function EditInvolvedModal({ involved, onClose, onSave }: Props) {
  const [nombre, setNombre] = useState("");
  const [celular, setCelular] = useState("");
  const [correo, setCorreo] = useState("");
  const [theme, setTheme] = useState("emerald");
  const [errorGeneral, setErrorGeneral] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<{ nombre?: string; celular?: string; correo?: string }>({});

  useEffect(() => {
    const update = () => {
      setTheme(document.querySelector("[data-theme]")?.getAttribute("data-theme") || "emerald");
    };
    update();
    const observer = new MutationObserver(update);
    const node = document.querySelector("[data-theme]");
    if (node) observer.observe(node, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);

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

  const validate = () => {
    const e: typeof errors = {};
    if (!nombre.trim()) e.nombre = "El nombre es requerido";
    else if (nombre.length > 100) e.nombre = "Máximo 100 caracteres";
    if (!celular.trim()) e.celular = "El celular es requerido";
    else if (!/^\d+$/.test(celular)) e.celular = "Solo números";
    else if (celular.length < 7 || celular.length > 15) e.celular = "Entre 7 y 15 dígitos";
    if (!correo.trim()) e.correo = "El correo es requerido";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(correo)) e.correo = "Correo inválido";
    setErrors(e);
    return Object.keys(e).length === 0;
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
    } catch {
      setErrorGeneral("Error al actualizar el involucrado");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setNombre(""); setCelular(""); setCorreo("");
    setErrors({}); setErrorGeneral(""); setIsSubmitting(false);
    onClose();
  };

  if (!involved) return null;

  return createPortal(
    <div
      data-theme={theme}
      className="fixed inset-0 z-[999999] flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={handleClose}
    >
      <div
        className="bg-base-100 rounded-2xl w-full max-w-lg mx-4 shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal header con color */}
        <div className="bg-gradient-to-r from-success/20 to-success/5 border-b border-base-300 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-success/15 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </div>
            <div>
              <h3 className="font-bold text-base-content">Editar Involucrado</h3>
              <p className="text-xs text-base-content/60">Modifica los datos de contacto</p>
            </div>
          </div>
          <button onClick={handleClose} className="btn btn-ghost btn-sm btn-circle">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6 space-y-4">
          {/* Info documento (no editable) */}
          <div className="bg-base-200/70 rounded-xl p-3 flex items-center gap-3 border border-base-300">
            <svg className="w-4 h-4 text-base-content/50 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M10 6H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V5a2 2 0 114 0v1m-4 0a2 2 0 104 0m-5 8a2 2 0 100-4 2 2 0 000 4zm0 0c1.306 0 2.417.835 2.83 2M9 14a3.001 3.001 0 00-2.83 2M15 11h3m-3 4h2" />
            </svg>
            <div className="flex items-center gap-4 text-sm flex-wrap">
              <span><span className="text-base-content/50">Tipo:</span> <strong>{involved.tipo_documento}</strong></span>
              <span><span className="text-base-content/50">Número:</span> <strong className="font-mono">{involved.numero_documento}</strong></span>
              {involved.tipo_documento === "NIT" && involved.digito_verificacion && (
                <span><span className="text-base-content/50">DV:</span> <strong>{involved.digito_verificacion}</strong></span>
              )}
            </div>
          </div>

          {errorGeneral && (
            <div className="alert alert-error py-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm">{errorGeneral}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Nombre */}
            <div className="form-control">
              <label className="label py-1">
                <span className="label-text font-medium">Nombre <span className="text-error">*</span></span>
              </label>
              <input
                type="text"
                className={`input input-bordered ${errors.nombre ? "input-error" : ""}`}
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                maxLength={100}
                disabled={isSubmitting}
                placeholder="Nombre completo"
              />
              {errors.nombre && <label className="label py-0"><span className="label-text-alt text-error">{errors.nombre}</span></label>}
            </div>

            {/* Celular y Correo en grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="form-control">
                <label className="label py-1">
                  <span className="label-text font-medium">Celular <span className="text-error">*</span></span>
                </label>
                <input
                  type="text"
                  className={`input input-bordered ${errors.celular ? "input-error" : ""}`}
                  value={celular}
                  onChange={(e) => setCelular(e.target.value)}
                  maxLength={15}
                  disabled={isSubmitting}
                  placeholder="Número celular"
                />
                {errors.celular && <label className="label py-0"><span className="label-text-alt text-error">{errors.celular}</span></label>}
              </div>
              <div className="form-control">
                <label className="label py-1">
                  <span className="label-text font-medium">Correo <span className="text-error">*</span></span>
                </label>
                <input
                  type="email"
                  className={`input input-bordered ${errors.correo ? "input-error" : ""}`}
                  value={correo}
                  onChange={(e) => setCorreo(e.target.value)}
                  disabled={isSubmitting}
                  placeholder="correo@ejemplo.com"
                />
                {errors.correo && <label className="label py-0"><span className="label-text-alt text-error">{errors.correo}</span></label>}
              </div>
            </div>

            {/* Botones */}
            <div className="flex justify-end gap-3 pt-2 border-t border-base-300">
              <button type="button" onClick={handleClose} className="btn btn-ghost" disabled={isSubmitting}>
                Cancelar
              </button>
              <button type="submit" className="btn btn-success text-white gap-2" disabled={isSubmitting}>
                {isSubmitting ? (
                  <><span className="loading loading-spinner loading-sm" />Guardando...</>
                ) : (
                  <><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>Guardar Cambios</>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>,
    document.body
  );
}
