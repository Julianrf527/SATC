import { useState } from "react";
import { apiCall, API_CONFIG } from "../../../../utils/api";

type TipoOption = {
  value: "AUTO_REQUERIMIENTO" | "OFICIO" | "RESOLUCION_ARCHIVO";
  label: string;
  description: string;
};

const TIPO_OPTIONS: TipoOption[] = [
  {
    value: "AUTO_REQUERIMIENTO",
    label: "Auto de Requerimiento",
    description: "Emite un auto con notificación a los involucrados",
  },
  {
    value: "OFICIO",
    label: "Oficio remitido por competencia",
    description: "La infracción se remite a otra entidad",
  },
  {
    value: "RESOLUCION_ARCHIVO",
    label: "Resolución de Archivo",
    description: "Se acoge el concepto archivando el trámite",
  },
];

type Props = {
  etapaConceptoId: number;
  expedienteId: number;
  tipoActual: "AUTO_REQUERIMIENTO" | "OFICIO" | "RESOLUCION_ARCHIVO";
  isEditable: boolean;
  setToast: (t: { id: number; message: string; type: "success" | "error" }) => void;
  onTipoUpdated: (nuevoTipo: string) => void;
};

export default function ConceptoData({
  etapaConceptoId,
  expedienteId: _expedienteId,
  tipoActual,
  isEditable,
  setToast,
  onTipoUpdated,
}: Props) {
  const [showEdit, setShowEdit] = useState(false);
  const [selectedTipo, setSelectedTipo] = useState(tipoActual);
  const [showWarning, setShowWarning] = useState(false);
  const [pendingTipo, setPendingTipo] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const currentOption = TIPO_OPTIONS.find((o) => o.value === tipoActual);

  const handleEditClick = () => {
    setSelectedTipo(tipoActual);
    setShowEdit(true);
  };

  const handleCancel = () => {
    setShowEdit(false);
    setSelectedTipo(tipoActual);
    setShowWarning(false);
    setPendingTipo(null);
  };

  const handleSave = async () => {
    if (selectedTipo === tipoActual) {
      setShowEdit(false);
      return;
    }
    // Warn before changing tipo (will delete associated data)
    setPendingTipo(selectedTipo);
    setShowWarning(true);
  };

  const handleConfirmChange = async () => {
    if (!pendingTipo) return;
    setIsSubmitting(true);
    setShowWarning(false);
    try {
      const res = await apiCall(
        API_CONFIG.ENDPOINTS.INFRACTION_PUT_CONCEPTO(etapaConceptoId),
        {
          method: "PUT",
          body: JSON.stringify({ tipo_acogida_concepto: pendingTipo }),
        },
      );
      if (res.ok) {
        setToast({ id: Date.now(), message: res.message || "Tipo de acogida actualizado", type: res.cierre_eliminado ? "error" : "success" });
        setShowEdit(false);
        onTipoUpdated(pendingTipo);
      } else {
        setToast({ id: Date.now(), message: res.detail || "Error al actualizar", type: "error" });
      }
    } catch {
      setToast({ id: Date.now(), message: "Error de conexión", type: "error" });
    } finally {
      setIsSubmitting(false);
      setPendingTipo(null);
    }
  };

  return (
    <div className="card bg-base-100 shadow-md border border-base-300">
      <div className="card-body">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-warning/10 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <div>
              <h3 className="text-xl font-bold">Acogida del Concepto Técnico</h3>
              <p className="text-sm text-base-content/60">¿Cómo se acoge el concepto de visita?</p>
            </div>
          </div>
          {!showEdit && isEditable && (
            <button
              className="btn btn-ghost btn-sm gap-2 text-warning hover:bg-warning/10"
              onClick={handleEditClick}
              disabled={isSubmitting}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Editar
            </button>
          )}
        </div>

        {/* Vista datos */}
        {!showEdit && (
          <div className="flex items-start gap-4 p-4 bg-warning/5 rounded-xl">
            <div className="w-8 h-8 bg-warning/20 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
              <svg className="w-4 h-4 text-warning" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium text-base-content/50 uppercase tracking-wide mb-1">Tipo seleccionado</p>
              <p className="font-semibold text-base-content">{currentOption?.label ?? tipoActual}</p>
              <p className="text-sm text-base-content/60 mt-1">{currentOption?.description}</p>
            </div>
          </div>
        )}

        {/* Formulario edición */}
        {showEdit && (
          <div className="space-y-3">
            <p className="text-sm text-base-content/60 mb-2">Seleccione cómo desea acoger el concepto técnico:</p>
            {TIPO_OPTIONS.map((opt) => (
              <label
                key={opt.value}
                className={`flex items-start gap-3 p-4 rounded-xl border cursor-pointer transition-all ${
                  selectedTipo === opt.value
                    ? "border-base-300 bg-warning/5"
                    : "border-base-300 hover:bg-base-200/60"
                }`}
              >
                <input
                  type="radio"
                  name="tipo_acogida"
                  value={opt.value}
                  checked={selectedTipo === opt.value}
                  onChange={() => setSelectedTipo(opt.value)}
                  className="radio radio-warning mt-0.5"
                  disabled={isSubmitting}
                />
                <div>
                  <p className="font-medium text-sm">{opt.label}</p>
                  <p className="text-xs text-base-content/50 mt-0.5">{opt.description}</p>
                </div>
              </label>
            ))}
            <div className="flex gap-3 justify-end pt-2 border-t border-base-300">
              <button type="button" className="btn btn-outline btn-sm" onClick={handleCancel} disabled={isSubmitting}>
                Cancelar
              </button>
              <button
                type="button"
                className="btn btn-warning btn-sm text-white"
                onClick={handleSave}
                disabled={isSubmitting}
              >
                {isSubmitting ? <span className="loading loading-spinner loading-xs" /> : "Guardar"}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Warning modal */}
      {showWarning && (
        <div className="modal modal-open">
          <div className="modal-box">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-error/10 rounded-full flex items-center justify-center">
                <svg className="w-5 h-5 text-error" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h3 className="font-bold text-lg">Cambio de tipo de acogida</h3>
            </div>
            <p className="text-base-content/80 mb-2">
              Cambiar el tipo de acogida eliminará <span className="font-semibold text-error">toda la información</span> registrada
              actualmente para este concepto:
            </p>
            <ul className="text-sm text-base-content/60 list-disc list-inside mb-4 space-y-1">
              <li>Acto administrativo y notificaciones</li>
              <li>Comunicaciones registradas</li>
              <li>Oficio remite</li>
              <li>Días de término y fecha calculada</li>
            </ul>
            <p className="text-sm font-medium text-base-content">¿Está seguro de que desea continuar?</p>
            <div className="modal-action">
              <button className="btn btn-outline" onClick={() => { setShowWarning(false); setPendingTipo(null); }}>
                Cancelar
              </button>
              <button className="btn btn-error text-white" onClick={handleConfirmChange} disabled={isSubmitting}>
                {isSubmitting ? <span className="loading loading-spinner loading-sm" /> : "Sí, cambiar tipo"}
              </button>
            </div>
          </div>
          <div className="modal-backdrop" onClick={() => { setShowWarning(false); setPendingTipo(null); }} />
        </div>
      )}
    </div>
  );
}
