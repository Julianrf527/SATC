import { AlertasExpediente, type AlertaPaginada } from "@features/alertas";
import { API_CONFIG } from "@shared/lib/api";
import { useAuth } from "@shared/context/AuthContext";
import type { SetToast } from "../types";
import { destinoAlertaRecurso, estadoExpedienteAlerta } from "./alertasRecurso";

/**
 * Pestaña Alertas (/recurso/alerts, `recurso_gestionar` o `recurso_consultar`):
 * "Mías" son las alertas en las que el usuario es el encargado; "Todos", todas.
 * Las reglas y plazos viven en el backend (app-recurso/services/alertas.py).
 *
 * El botón de cada alerta lo decide `destinoAlertaRecurso`: al técnico le abre
 * su proceso en Mis actuaciones; a quien gestiona, el expediente en Gestionar;
 * a los demás, en Consulta (en la pestaña de la etapa de la alerta).
 */
export default function AlertasRecursoLayout({ setToast }: { setToast: SetToast }) {
  const { user } = useAuth();
  const permisos = (user?.permisos ?? []).map((p) => p?.name);
  const destino = (alerta: AlertaPaginada) => destinoAlertaRecurso(alerta, permisos);
  return (
    <AlertasExpediente
      alertsAllEndpoint={API_CONFIG.ENDPOINTS.RECURSO_ALERTAS_ALL}
      rutas={{ gestion: "/recurso/manage", consulta: "/recurso/consult" }}
      processName="Concesiones de Aguas"
      setToast={setToast}
      estadoNavegacion={estadoExpedienteAlerta}
      destino={destino}
    />
  );
}
