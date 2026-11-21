import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@shared/context/AuthContext";

type Destino = {
  expediente_radicado: string | null;
  /** Pestaña de la etapa del documento (`pestanaDeActuacion`). */
  etapa: string;
  /** Soy el encargado actual del expediente: lo abro en Gestionar. */
  gestionar: boolean;
};

/**
 * Abre el expediente en la pestaña de la etapa del documento (como el
 * `useIrAlExpediente` de recurso): en Gestionar si soy su encargado actual,
 * si no en Consulta. `puedeIr` = false si no tengo ninguna de las dos.
 */
export function useIrAlExpediente() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const permisos = new Set((user?.permisos ?? []).map((p) => p?.name));
  const gestiona = permisos.has("infraccion_gestionar");
  const consulta = permisos.has("infraccion_consultar");

  const ir = useCallback(
    (d: Destino) => {
      const ruta = d.gestionar && gestiona ? "/infraction/manage" : consulta ? "/infraction/consult" : null;
      if (!ruta || !d.expediente_radicado) return;
      navigate(ruta, {
        state: { radicadoToSelect: d.expediente_radicado, etapaToSelect: d.etapa, timestamp: Date.now() },
      });
    },
    [navigate, gestiona, consulta],
  );

  return { puedeIr: gestiona || consulta, gestiona, ir };
}
