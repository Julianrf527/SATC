import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { X, UserCheck, Calendar } from "lucide-react";
import type { ProfesionalDisponible } from "../../../types/infraccionApp";
import { getErrorMessage } from "../../../utils/api";
import CustomSelect from "../../Common/Form/CustomSelect";
import CustomDateInput from "../../Common/Form/CustomDateInput";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (
    profesionalId: number,
    revisorId: number,
    fechaProgramacion: string,
  ) => Promise<void>;
  profesionales: ProfesionalDisponible[];
  revisores: ProfesionalDisponible[];
  /** Si es reasignación, pasar el profesional actual para mostrarlo */
  profesionalActualId?: number | null;
  /** Si es reasignación, pasar el revisor actual para mostrarlo */
  revisorActualId?: number | null;
  /** Fecha de programación actual */
  fechaProgramacionActual?: string | null;
  isReassign?: boolean;
};

export default function AsignarProfesionalModal({
  isOpen,
  onClose,
  onSubmit,
  profesionales,
  revisores,
  profesionalActualId,
  revisorActualId,
  fechaProgramacionActual,
  isReassign = false,
}: Props) {
  const [profesionalId, setProfesionalId] = useState<number | "">("");
  const [revisorId, setRevisorId] = useState<number | "">("");
  const [fechaProgramacion, setFechaProgramacion] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [theme, setTheme] = useState("emerald");

  useEffect(() => {
    if (isOpen) {
      setProfesionalId(profesionalActualId ?? "");
      setRevisorId(revisorActualId ?? "");
      setFechaProgramacion(fechaProgramacionActual ?? "");
      setError("");
      setSubmitting(false);
    }
  }, [isOpen, profesionalActualId, revisorActualId, fechaProgramacionActual]);

  useEffect(() => {
    const update = () => {
      const t = document.querySelector("[data-theme]")?.getAttribute("data-theme") || "emerald";
      setTheme(t);
    };
    update();
    const obs = new MutationObserver(update);
    const node = document.querySelector("[data-theme]");
    if (node) obs.observe(node, { attributes: true, attributeFilter: ["data-theme"] });
    return () => obs.disconnect();
  }, []);

  const handleSubmit = async () => {
    if (!profesionalId) {
      setError("Selecciona un profesional");
      return;
    }
    if (!revisorId) {
      setError("Selecciona un revisor");
      return;
    }
    if (revisorId === profesionalId) {
      setError("El profesional y el revisor deben ser personas distintas");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      await onSubmit(Number(profesionalId), Number(revisorId), fechaProgramacion);
      onClose();
    } catch (e) {
      setError(getErrorMessage(e, "Error al asignar el profesional"));
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return createPortal(
    <div
      data-theme={theme}
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-base-100 rounded-xl w-full max-w-md mx-4 shadow-2xl border border-base-300"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-base-300">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-success/10 rounded-lg flex items-center justify-center">
              <UserCheck className="text-success" size={18} />
            </div>
            <div>
              <h3 className="font-bold text-base text-base-content">
                {isReassign ? "Reasignar Profesional" : "Asignar Profesional"}
              </h3>
              <p className="text-xs text-base-content/50">
                {isReassign
                  ? "El proceso anterior será finalizado automáticamente"
                  : "Se creará el proceso de cargue de informe"}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="btn btn-ghost btn-sm btn-circle" disabled={submitting}>
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          {isReassign && (
            <div className="alert alert-warning py-2">
              <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <span className="text-xs">El proceso de documentos actual será cancelado y el profesional anterior será notificado.</span>
            </div>
          )}

          {/* Selector de profesional */}
          <div className="form-control">
            <label className="label py-1">
              <span className="label-text font-medium">Profesional <span className="text-error">*</span></span>
            </label>
            <CustomSelect
              value={profesionalId === "" ? 0 : profesionalId}
              onChange={(v) => setProfesionalId(v === 0 ? "" : v)}
              placeholder="Seleccionar profesional..."
              disabled={submitting}
              options={profesionales.map((p) => ({ value: p.id, label: p.nombre }))}
            />
          </div>

          {/* Selector de revisor */}
          <div className="form-control">
            <label className="label py-1">
              <span className="label-text font-medium">Revisor <span className="text-error">*</span></span>
            </label>
            <CustomSelect
              value={revisorId === "" ? 0 : revisorId}
              onChange={(v) => setRevisorId(v === 0 ? "" : v)}
              placeholder="Seleccionar revisor..."
              disabled={submitting}
              options={revisores.map((r) => ({ value: r.id, label: r.nombre }))}
            />
          </div>

          {/* Fecha de programación */}
          <div className="form-control">
            <label className="label py-1">
              <span className="label-text font-medium flex items-center gap-1">
                <Calendar size={14} />
                Fecha de Programación de Visita
                <span className="text-base-content/40 text-xs font-normal">(Opcional)</span>
              </span>
            </label>
            <CustomDateInput
              value={fechaProgramacion}
              onChange={setFechaProgramacion}
              disabled={submitting}
            />
          </div>

          {error && (
            <div className="alert alert-error py-2">
              <span className="text-sm">{error}</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-6 py-4 border-t border-base-300">
          <button onClick={onClose} className="btn btn-ghost btn-sm" disabled={submitting}>
            Cancelar
          </button>
          <button
            onClick={handleSubmit}
            className="btn btn-success text-white btn-sm gap-2"
            disabled={submitting || !profesionalId || !revisorId}
          >
            {submitting ? (
              <><span className="loading loading-spinner loading-xs" />Procesando...</>
            ) : (
              <><UserCheck size={15} />{isReassign ? "Reasignar" : "Asignar"}</>
            )}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
