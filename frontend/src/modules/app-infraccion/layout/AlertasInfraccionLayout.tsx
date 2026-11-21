import { AlertasExpediente, type AlertaPaginada, type EtiquetasAlcance } from "@features/alertas";
import { API_CONFIG } from "@shared/lib/api";
import { useAuth } from "@shared/context/AuthContext";
import { destinoAlertaInfraccion, estadoExpedienteAlerta } from "./alertasInfraccion";

type Props = {
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
};

/**
 * Pestaña Alertas (/infraction/alerts, `infraccion_alertas`): "Mis alertas"
 * son las que le tocan al usuario ahora (como abogado, técnico o líder
 * técnico asignado, o por su rol: asignar informes, líder de proyecto);
 * "Todas", todas. Reglas y plazos: app-infraction/services/alertas.py.
 * El botón de cada alerta lo decide `destinoAlertaInfraccion`.
 */
const ETIQUETAS_ALCANCE: EtiquetasAlcance = { titulo: "Alertas", mios: "Mis alertas", todos: "Todas" };

export default function AlertasInfraccionLayout({ setToast }: Props) {
  const { user } = useAuth();
  const permisos = (user?.permisos ?? []).map((p) => p?.name);
  const destino = (alerta: AlertaPaginada) => destinoAlertaInfraccion(alerta, permisos);
  return (
    <AlertasExpediente
      alertsAllEndpoint={API_CONFIG.ENDPOINTS.INFRACTION_ALERTS_ALL}
      rutas={{ gestion: "/infraction/manage", consulta: "/infraction/consult" }}
      processName="Módulo de Infracciones"
      setToast={setToast}
      estadoNavegacion={estadoExpedienteAlerta}
      destino={destino}
      etiquetasAlcance={ETIQUETAS_ALCANCE}
    />
  );
}
