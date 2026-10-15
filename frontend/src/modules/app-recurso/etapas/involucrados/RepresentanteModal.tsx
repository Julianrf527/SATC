import { useState } from "react";
import { AlertCircle, UserCog } from "lucide-react";
import { Modal } from "@shared/ui";
import {
  resolverPersona,
  useCambiarRepresentanteMutation,
  useCambiarRepresentanteTerceroMutation,
} from "../../api/involucrados";
import { mensajeError } from "../../api/errors";
import type { SetToast, VinculoInvolucrado } from "../../types";
import PersonaFields from "./PersonaFields";
import { nombrePersona, validarPersona } from "./personaForm";
import { usePersonaForm } from "./usePersonaForm";

type Props = {
  expedienteId: number;
  vinculo: VinculoInvolucrado;
  setToast: SetToast;
  onClose: () => void;
};

/** Cambia el representante legal de un solicitante o tercero interviniente (PATCH con `version`). */
export default function RepresentanteModal({ expedienteId, vinculo, setToast, onClose }: Props) {
  const persona = usePersonaForm(setToast);
  const [error, setError] = useState<string | null>(null);
  const [resolviendo, setResolviendo] = useState(false);
  const cambiarSolicitante = useCambiarRepresentanteMutation(expedienteId);
  const cambiarTercero = useCambiarRepresentanteTerceroMutation(expedienteId);
  // El de un tercero interviniente se cambia por /terceros (C.10).
  const cambiar = vinculo.tipo_vinculo === "TERCERO_INTERVINIENTE" ? cambiarTercero : cambiarSolicitante;
  const ocupado = resolviendo || cambiar.isPending;

  const guardar = async () => {
    const invalido = validarPersona(persona.form, persona.existente, "representante legal");
    if (invalido) {
      setError(invalido);
      return;
    }
    setError(null);
    setResolviendo(true);
    let representanteId: number;
    try {
      representanteId = await resolverPersona(persona.existente, persona.form);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al registrar la persona");
      return;
    } finally {
      setResolviendo(false);
    }
    cambiar.mutate(
      { vinculo, representanteId },
      {
        onSuccess: () => {
          setToast({ id: Date.now(), message: "Representante legal actualizado", type: "success" });
          onClose();
        },
        onError: (err) => setError(mensajeError(err, "Error al cambiar el representante")),
      },
    );
  };

  return (
    <Modal
      isOpen
      onClose={onClose}
      size="xl"
      icon={<UserCog size={20} />}
      title="Representante legal"
      subtitle={nombrePersona(vinculo.involucrado)}
      closeOnEsc={!ocupado}
      closeOnBackdrop={!ocupado}
      footer={
        <>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose} disabled={ocupado}>
            Cancelar
          </button>
          <button type="button" className="btn btn-warning btn-sm text-white" onClick={() => void guardar()} disabled={ocupado}>
            {ocupado && <span className="loading loading-spinner loading-xs" />}
            Guardar
          </button>
        </>
      }
    >
      {vinculo.representante && (
        <p className="text-sm text-base-content/70 mb-3">
          Actual: <span className="font-medium text-base-content">{nombrePersona(vinculo.representante)}</span>
        </p>
      )}
      <PersonaFields titulo="Nuevo representante legal" persona={persona} disabled={ocupado} />
      {error && (
        <div role="alert" className="alert alert-error py-2 text-sm mt-4">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}
    </Modal>
  );
}
