import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { apiCall, API_CONFIG } from "../../../utils/api";
import CustomSelect from "../../Common/Form/CustomSelect";

type Involved = {
  id: number;
  numero_documento: number;
  digito_verificacion: string | null;
  tipo_documento: string;
  nombre: string;
  celular: number | null;
  correo: string | null;
  direccion?: string | null;
};

type SaveData = {
  nombre: string;
  numero_documento?: number;
  tipo_documento?: string;
  celular: number | null;
  correo: string | null;
  digito_verificacion: string | null;
  direccion: string | null;
};

type Props = {
  involved: Involved | null;
  onClose: () => void;
  onSave: (id: number, data: SaveData) => Promise<void>;
};

const DOC_TYPES = ["CC", "NIT", "CE", "PP", "TI"];

export default function EditInvolvedModal({ involved, onClose, onSave }: Props) {
  const [nombre, setNombre] = useState("");
  const [tipoDoc, setTipoDoc] = useState("CC");
  const [numDoc, setNumDoc] = useState("");
  const [dv, setDv] = useState("");
  const [celular, setCelular] = useState("");
  const [correo, setCorreo] = useState("");
  const [direccion, setDireccion] = useState("");
  const [theme, setTheme] = useState("emerald");
  const [errorGeneral, setErrorGeneral] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isCheckingDoc, setIsCheckingDoc] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    const update = () =>
      setTheme(document.querySelector("[data-theme]")?.getAttribute("data-theme") || "emerald");
    update();
    const observer = new MutationObserver(update);
    const node = document.querySelector("[data-theme]");
    if (node) observer.observe(node, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (involved) {
      setNombre(involved.nombre);
      setTipoDoc(involved.tipo_documento);
      setNumDoc(String(involved.numero_documento));
      setDv(involved.digito_verificacion ?? "");
      setCelular(involved.celular != null ? String(involved.celular) : "");
      setCorreo(involved.correo ?? "");
      setDireccion(involved.direccion ?? "");
      setErrors({});
      setErrorGeneral("");
      setIsSubmitting(false);
    }
  }, [involved]);

  const docCambio = () =>
    involved &&
    (numDoc !== String(involved.numero_documento) ||
      tipoDoc !== involved.tipo_documento ||
      (tipoDoc === "NIT" && dv !== (involved.digito_verificacion ?? "")));

  const validate = () => {
    const e: Record<string, string> = {};
    if (!nombre.trim()) e.nombre = "Requerido";
    else if (nombre.length > 100) e.nombre = "Máximo 100 caracteres";
    if (!numDoc.trim() || numDoc.length < 6) e.numDoc = "Mínimo 6 dígitos";
    if (tipoDoc === "NIT" && !dv.trim()) e.dv = "Requerido para NIT";
    if (celular.trim() && (celular.length < 7 || celular.length > 15))
      e.celular = "Entre 7 y 15 dígitos";
    if (correo.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(correo))
      e.correo = "Correo inválido";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorGeneral("");
    if (!involved || !validate()) return;

    // Uniqueness check if doc changed
    if (docCambio()) {
      setIsCheckingDoc(true);
      try {
        const dvParam = tipoDoc === "NIT" ? dv : undefined;
        const res = await apiCall(API_CONFIG.ENDPOINTS.INVOLVED_SEARCH(tipoDoc, numDoc, dvParam));
        if (res.ok && res.data && res.data.id !== involved.id) {
          setErrors((prev) => ({ ...prev, numDoc: "Ya existe un involucrado con ese documento" }));
          setIsCheckingDoc(false);
          return;
        }
      } catch {
        // 404 = no existe, continuar
      } finally {
        setIsCheckingDoc(false);
      }
    }

    setIsSubmitting(true);
    try {
      const payload: SaveData = {
        nombre: nombre.trim(),
        celular: celular.trim() ? parseInt(celular.trim()) : null,
        correo: correo.trim() ? correo.trim().toLowerCase() : null,
        digito_verificacion: tipoDoc === "NIT" ? (dv.trim() || null) : null,
        direccion: direccion.trim() || null,
      };
      if (docCambio()) {
        payload.numero_documento = parseInt(numDoc.trim());
        payload.tipo_documento = tipoDoc;
      }
      await onSave(involved.id, payload);
      handleClose();
    } catch {
      setErrorGeneral("Error al actualizar el involucrado");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setNombre(""); setTipoDoc("CC"); setNumDoc(""); setDv("");
    setCelular(""); setCorreo(""); setDireccion(""); setErrors({}); setErrorGeneral("");
    setIsSubmitting(false);
    onClose();
  };

  if (!involved) return null;

  const busy = isSubmitting || isCheckingDoc;

  return createPortal(
    <div
      data-theme={theme}
      className="fixed inset-0 z-[999999] flex items-center justify-center bg-black/50 backdrop-blur-sm p-3 sm:p-4"
      onClick={handleClose}
    >
      <div
        className="bg-base-100 rounded-2xl w-full max-w-[540px] shadow-2xl border border-base-300 overflow-hidden max-h-[92vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-success/10 border-b border-base-300 px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-success/15 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </div>
            <div>
              <h3 className="font-bold text-lg text-base-content leading-tight">Editar Involucrado</h3>
              <p className="text-xs text-base-content/60">Modifica los datos del involucrado</p>
            </div>
          </div>
          <button onClick={handleClose} className="btn btn-ghost btn-sm btn-circle text-base-content/70">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-5 space-y-4 overflow-y-auto">
          {errorGeneral && (
            <div className="alert alert-error py-2 text-sm">
              <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {errorGeneral}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Documento */}
            <div>
              <p className="text-xs font-semibold text-base-content/50 uppercase tracking-wider mb-2">Documento</p>
              <div className="grid grid-cols-3 gap-3">
                {/* Tipo */}
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-base-content/60">Tipo *</span>
                  <CustomSelect
                    value={DOC_TYPES.indexOf(tipoDoc)}
                    onChange={(i) => {
                      const t = DOC_TYPES[i];
                      setTipoDoc(t);
                      if (t !== "NIT") setDv("");
                    }}
                    hidePlaceholderOption
                    className="select-sm"
                    disabled={busy}
                    options={DOC_TYPES.map((t, i) => ({ value: i, label: t }))}
                  />
                </div>

                {/* Número (ocupa 2 cols) */}
                <div className={`flex flex-col gap-1 ${tipoDoc === "NIT" ? "" : "col-span-2"}`}>
                  <span className="text-xs font-medium text-base-content/60">Número *</span>
                  <input
                    type="text"
                    value={numDoc}
                    onChange={(e) => setNumDoc(e.target.value.replace(/\D/g, ""))}
                    className={`input input-bordered input-sm w-full font-mono ${errors.numDoc ? "input-error" : ""}`}
                    disabled={busy}
                    maxLength={15}
                    placeholder="Número"
                  />
                  {errors.numDoc && <span className="text-[11px] text-error">{errors.numDoc}</span>}
                </div>

                {/* DV solo NIT */}
                {tipoDoc === "NIT" && (
                  <div className="flex flex-col gap-1">
                    <span className="text-xs font-medium text-base-content/60">DV *</span>
                    <input
                      type="text"
                      value={dv}
                      onChange={(e) => setDv(e.target.value.replace(/\D/g, "").slice(0, 2))}
                      className={`input input-bordered input-sm w-full text-center font-mono ${errors.dv ? "input-error" : ""}`}
                      disabled={busy}
                      placeholder="00"
                    />
                    {errors.dv && <span className="text-[11px] text-error">{errors.dv}</span>}
                  </div>
                )}
              </div>
              {docCambio() && (
                <p className="text-[11px] text-warning mt-1.5 flex items-center gap-1">
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  Documento cambiado — se verificará unicidad al guardar
                </p>
              )}
            </div>

            <div className="divider my-1" />

            {/* Nombre */}
            <div className="flex flex-col gap-1">
              <span className="text-xs font-medium text-base-content/60">Nombre completo *</span>
              <input
                type="text"
                className={`input input-bordered w-full ${errors.nombre ? "input-error" : ""}`}
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                maxLength={100}
                disabled={busy}
                placeholder="Nombre completo o razón social"
              />
              {errors.nombre && <span className="text-[11px] text-error">{errors.nombre}</span>}
            </div>

            {/* Celular y Correo */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="flex flex-col gap-1">
                <span className="text-xs font-medium text-base-content/60">Celular</span>
                <input
                  type="text"
                  className={`input input-bordered w-full font-mono ${errors.celular ? "input-error" : ""}`}
                  value={celular}
                  onChange={(e) => setCelular(e.target.value.replace(/\D/g, ""))}
                  maxLength={15}
                  disabled={busy}
                  placeholder="3001234567"
                />
                {errors.celular && <span className="text-[11px] text-error">{errors.celular}</span>}
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-xs font-medium text-base-content/60">Correo</span>
                <input
                  type="email"
                  className={`input input-bordered w-full ${errors.correo ? "input-error" : ""}`}
                  value={correo}
                  onChange={(e) => setCorreo(e.target.value)}
                  disabled={busy}
                  placeholder="correo@ejemplo.com"
                />
                {errors.correo && <span className="text-[11px] text-error">{errors.correo}</span>}
              </div>
            </div>

            {/* Dirección */}
            <div className="flex flex-col gap-1">
              <span className="text-xs font-medium text-base-content/60">Dirección</span>
              <input
                type="text"
                className="input input-bordered w-full"
                value={direccion}
                onChange={(e) => setDireccion(e.target.value)}
                maxLength={200}
                disabled={busy}
                placeholder="Dirección de residencia o notificación"
              />
            </div>

            {/* Botones */}
            <div className="flex justify-end gap-3 pt-3 border-t border-base-300">
              <button type="button" onClick={handleClose} className="btn btn-ghost btn-sm" disabled={busy}>
                Cancelar
              </button>
              <button type="submit" className="btn btn-success btn-sm text-white gap-2 min-w-[150px]" disabled={busy}>
                {busy ? (
                  <>
                    <span className="loading loading-spinner loading-xs" />
                    {isCheckingDoc ? "Verificando..." : "Guardando..."}
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    Guardar Cambios
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>,
    document.body,
  );
}
