import { useState, type FormEvent } from "react";
import { AlertCircle, UserPlus } from "lucide-react";
import { resolverPersona, useVincularSolicitanteMutation, useVincularTerceroMutation } from "../../api/involucrados";
import { mensajeError } from "../../api/errors";
import type { SetToast } from "../../types";
import PersonaFields from "./PersonaFields";
import { validarPersona } from "./personaForm";
import { usePersonaForm } from "./usePersonaForm";

type Props = {
  expedienteId: number;
  setToast: SetToast;
  onCerrar: () => void;
  /** Vincula un tercero interviniente (C.10) en vez de un solicitante. */
  tercero?: boolean;
};

/**
 * Vincula un solicitante (plan §3): se busca o crea la persona en
 * app-involved y se vincula en app-recurso. Si es empresa (NIT) se pide su
 * representante legal (V14; el backend también lo exige).
 */
export default function VincularSolicitanteForm({ expedienteId, setToast, onCerrar, tercero = false }: Props) {
  const solicitante = usePersonaForm(setToast);
  const representante = usePersonaForm(setToast);
  const [error, setError] = useState<string | null>(null);
  const [resolviendo, setResolviendo] = useState(false);
  const vincularSolicitante = useVincularSolicitanteMutation(expedienteId);
  const vincularTercero = useVincularTerceroMutation(expedienteId);
  const vincular = tercero ? vincularTercero : vincularSolicitante;
  const rol = tercero ? "tercero interviniente" : "solicitante";

  const esNit = (solicitante.existente?.tipo_documento ?? solicitante.form.tipo_documento) === "NIT";
  const ocupado = resolviendo || vincular.isPending || solicitante.buscando || representante.buscando;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const invalido =
      validarPersona(solicitante.form, solicitante.existente, rol) ??
      (esNit ? validarPersona(representante.form, representante.existente, "representante legal") : null);
    if (invalido) {
      setError(invalido);
      return;
    }
    setError(null);
    setResolviendo(true);
    let ids: { involucrado_id: number; representante_id: number | null };
    try {
      ids = {
        involucrado_id: await resolverPersona(solicitante.existente, solicitante.form),
        representante_id: esNit ? await resolverPersona(representante.existente, representante.form) : null,
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al registrar la persona");
      return;
    } finally {
      setResolviendo(false);
    }
    vincular.mutate(ids, {
      onSuccess: (res) => {
        setToast({ id: Date.now(), message: res.message ?? (tercero ? "Tercero interviniente vinculado" : "Solicitante vinculado"), type: "success" });
        onCerrar();
      },
      onError: (err) => setError(mensajeError(err, `Error al vincular el ${rol}`)),
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <PersonaFields titulo={tercero ? "Tercero interviniente" : "Solicitante"} persona={solicitante} disabled={ocupado} />

      {esNit && (
        <div className="border-t border-base-300 pt-4">
          <PersonaFields titulo="Representante legal *" persona={representante} disabled={ocupado} />
        </div>
      )}

      {error && (
        <div role="alert" className="alert alert-error py-2 text-sm">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      <div className="flex justify-end gap-2 pt-2 border-t border-base-300">
        <button type="button" onClick={onCerrar} className="btn btn-ghost btn-sm" disabled={ocupado}>
          Cancelar
        </button>
        <button type="submit" className="btn btn-warning btn-sm text-white gap-1.5" disabled={ocupado}>
          {ocupado ? <span className="loading loading-spinner loading-xs" /> : <UserPlus size={14} />}
          Vincular {rol}
        </button>
      </div>
    </form>
  );
}
