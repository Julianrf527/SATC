import { useState, useEffect } from "react";
import { UserCheck, Calendar } from "lucide-react";
import type { ProfesionalDisponible } from "../types";
import { getErrorMessage } from "@shared/lib/api";
import { Modal } from "@shared/ui";
import CustomSelect from "@shared/ui/form/CustomSelect";
import CustomDateInput from "@shared/ui/form/CustomDateInput";

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

  useEffect(() => {
    if (isOpen) {
      setProfesionalId(profesionalActualId ?? "");
      setRevisorId(revisorActualId ?? "");
      setFechaProgramacion(fechaProgramacionActual ?? "");
      setError("");
      setSubmitting(false);
    }
  }, [isOpen, profesionalActualId, revisorActualId, fechaProgramacionActual]);

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

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      size="md"
      icon={<UserCheck size={18} />}
      title={isReassign ? "Reasignar Profesional" : "Asignar Profesional"}
      subtitle={
        isReassign
          ? "El proceso vigente se cerrará y se creará uno nuevo"
          : "Se creará el proceso de revisión del informe"
      }
      closeOnEsc={!submitting}
      closeOnBackdrop={!submitting}
      footer={
        <>
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
        </>
      }
    >
      <div className="space-y-4">
        {isReassign && (
          <div role="status" className="alert alert-warning py-2">
            <span className="text-xs">
              El proceso de revisión actual será cerrado y el profesional anterior será notificado.
            </span>
          </div>
        )}

        <div className="flex flex-col">
          <span className="label py-1">
            <span className="text-sm text-base-content font-medium">Profesional <span className="text-error">*</span></span>
          </span>
          <CustomSelect
            value={profesionalId === "" ? 0 : profesionalId}
            onChange={(v) => setProfesionalId(v === 0 ? "" : v)}
            placeholder="Seleccionar profesional..."
            disabled={submitting}
            options={profesionales.map((p) => ({ value: p.id, label: p.nombre }))}
          />
        </div>

        <div className="flex flex-col">
          <span className="label py-1">
            <span className="text-sm text-base-content font-medium">Revisor <span className="text-error">*</span></span>
          </span>
          <CustomSelect
            value={revisorId === "" ? 0 : revisorId}
            onChange={(v) => setRevisorId(v === 0 ? "" : v)}
            placeholder="Seleccionar revisor..."
            disabled={submitting}
            options={revisores.map((r) => ({ value: r.id, label: r.nombre }))}
          />
        </div>

        <div className="flex flex-col">
          <span className="label py-1">
            <span className="text-sm text-base-content font-medium flex items-center gap-1">
              <Calendar size={14} />
              Fecha de Programación de Visita
              <span className="text-base-content/60 text-xs font-normal">(Opcional)</span>
            </span>
          </span>
          <CustomDateInput value={fechaProgramacion} onChange={setFechaProgramacion} disabled={submitting} />
        </div>

        {error && (
          <div role="alert" className="alert alert-error py-2">
            <span className="text-sm">{error}</span>
          </div>
        )}
      </div>
    </Modal>
  );
}
