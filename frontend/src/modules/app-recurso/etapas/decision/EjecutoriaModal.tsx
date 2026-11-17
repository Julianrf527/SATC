import { useState } from "react";
import { CalendarCheck } from "lucide-react";
import { RECURSO_ENDPOINTS } from "@shared/lib/api";
import type { SetToast } from "../../types";
import { CampoFecha } from "../comun/campos/Campos";
import ModalFormulario from "../comun/ModalFormulario";
import { useEscritura } from "../comun/useEscritura";

type Props = {
  expedienteId: number;
  version: number;
  actual: string | null;
  setToast: SetToast;
  onClose: () => void;
};

/**
 * Fecha de ejecutoria de la decisión (C.6, PUT con `version`). La diligencia
 * el abogado (10 días hábiles tras notificar si no hay recurso, o cuando queda
 * en firme); vacía la borra.
 */
export default function EjecutoriaModal({ expedienteId, version, actual, setToast, onClose }: Props) {
  const [fecha, setFecha] = useState(actual ?? "");
  const [error, setError] = useState<string | null>(null);
  const { ejecutar, ocupado } = useEscritura(expedienteId, setToast);

  const guardar = () => {
    if (!fecha && !actual) return setError("Indique la fecha de ejecutoria");
    setError(null);
    ejecutar(
      {
        peticion: () => ({
          url: RECURSO_ENDPOINTS.RECURSO_ETAPA_ACCION(expedienteId, "decision/ejecutoria"),
          method: "PUT",
          body: { version, fecha_ejecutoria: fecha || null },
        }),
      },
      { exito: "Fecha de ejecutoria guardada", error: "Error al guardar la fecha de ejecutoria", onSuccess: onClose, onError: setError },
    );
  };

  return (
    <ModalFormulario
      titulo="Fecha de ejecutoria"
      icono={<CalendarCheck size={20} />}
      ocupado={ocupado}
      error={error}
      textoGuardar={fecha || !actual ? "Guardar" : "Quitar fecha"}
      onGuardar={guardar}
      onClose={onClose}
      size="md"
    >
      <p className="text-sm text-base-content/70">
        10 días hábiles después de notificar si no hay recurso; si hay recurso, cuando la decisión queda en firme.
        {actual && " Deje la fecha vacía para borrarla."}
      </p>
      <CampoFecha etiqueta="Fecha de ejecutoria" valor={fecha} onChange={setFecha} />
    </ModalFormulario>
  );
}
