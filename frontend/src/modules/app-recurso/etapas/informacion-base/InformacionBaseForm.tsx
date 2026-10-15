import { useState, type FormEvent } from "react";
import { AlertCircle, RefreshCw, Save } from "lucide-react";
import { useActualizarExpedienteMutation } from "../../api/expedientes";
import { estadoError, MENSAJE_CONFLICTO, mensajeError } from "../../api/errors";
import ExpedienteFields from "../../manage/expediente-form/ExpedienteFields";
import {
  formDesdeDetalle,
  validarExpedienteForm,
  type ExpedienteFormState,
} from "../../manage/expediente-form/expedienteForm";
import type { CatalogosRecurso, ExpedienteDetalle, SetToast } from "../../types";

type Props = {
  expediente: ExpedienteDetalle;
  catalogos: CatalogosRecurso;
  setToast: SetToast;
  onCerrar: () => void;
};

/**
 * Edición de la información base con bloqueo optimista: se envía la
 * `version` leída. Ante 409 el detalle ya se recargó (la mutación invalida)
 * y aquí se ofrece volver a cargar el formulario con los datos nuevos.
 */
export default function InformacionBaseForm({ expediente, catalogos, setToast, onCerrar }: Props) {
  const [form, setFormState] = useState<ExpedienteFormState>(() => formDesdeDetalle(expediente));
  const [version, setVersion] = useState(expediente.version);
  const [error, setError] = useState<string | null>(null);
  const [conflicto, setConflicto] = useState(false);
  const actualizar = useActualizarExpedienteMutation(expediente.id);

  const setForm = (cambio: Partial<ExpedienteFormState>) => setFormState((prev) => ({ ...prev, ...cambio }));

  const recargar = () => {
    setFormState(formDesdeDetalle(expediente));
    setVersion(expediente.version);
    setConflicto(false);
    setError(null);
  };

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const invalido = validarExpedienteForm(form);
    if (invalido) {
      setError(invalido);
      return;
    }
    setError(null);
    actualizar.mutate(
      { form, version },
      {
        onSuccess: () => {
          setToast({ id: Date.now(), message: "Información base actualizada", type: "success" });
          onCerrar();
        },
        onError: (err) => {
          const detalle = mensajeError(err, err instanceof Error ? err.message : "Error al guardar");
          // 409 por versión vieja: el backend responde exactamente este mensaje.
          // Otros 409 (radicado o expediente repetido) se muestran tal cual.
          if (estadoError(err) === 409 && detalle === MENSAJE_CONFLICTO) {
            setConflicto(true);
            return;
          }
          setError(detalle);
        },
      },
    );
  };

  // La versión del servidor cambió mientras se editaba (refetch tras 409).
  const servidorCambio = expediente.version !== version;

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {(conflicto || servidorCambio) && (
        <div role="alert" className="alert alert-warning">
          <AlertCircle size={18} />
          <span className="flex-1">{MENSAJE_CONFLICTO}</span>
          <button type="button" className="btn btn-sm gap-1" onClick={recargar}>
            <RefreshCw size={14} />
            Recargar
          </button>
        </div>
      )}

      <ExpedienteFields
        form={form}
        setForm={setForm}
        catalogos={catalogos}
        disabled={actualizar.isPending}
        columnas="grid grid-cols-1 md:grid-cols-2 gap-4"
      />

      {error && (
        <div role="alert" className="alert alert-error shadow-sm">
          <AlertCircle className="w-5 h-5" />
          <span>{error}</span>
        </div>
      )}

      <div className="flex justify-end gap-3 pt-2 border-t border-base-300">
        <button type="button" className="btn btn-outline" onClick={onCerrar} disabled={actualizar.isPending}>
          Cancelar
        </button>
        <button type="submit" className="btn btn-success text-white gap-2" disabled={actualizar.isPending || conflicto}>
          {actualizar.isPending ? <span className="loading loading-spinner loading-sm" /> : <Save size={16} />}
          Guardar cambios
        </button>
      </div>
    </form>
  );
}
