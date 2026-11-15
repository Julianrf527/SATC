import { AlertasExpediente, type AlertaPaginada } from "@features/alertas";
import { API_CONFIG } from "@shared/lib/api";
import { useAuth } from "@shared/context/AuthContext";
import type { NavegacionExpediente, SetToast } from "../types";
import { pestanaDeAlerta, rutaExpedienteAlertas } from "./alertasRecurso";

/**
 * Pestaña Alertas (/recurso/alerts, `recurso_gestionar` o `recurso_consultar`):
 * "Mías" son las alertas en las que el usuario es el encargado; "Todos", todas.
 * Las reglas y plazos viven en el backend (app-recurso/services/alertas.py).
 *
 * El clic abre el expediente por id en la pestaña de la etapa de la alerta:
 * en Gestionar si el usuario gestiona y en Consulta si solo consulta.
 */
function estadoNavegacion(alerta: AlertaPaginada): NavegacionExpediente {
  return { expedienteIdToSelect: alerta.expediente_id, pestanaToSelect: pestanaDeAlerta(alerta.tipo) };
}

export default function AlertasRecursoLayout({ setToast }: { setToast: SetToast }) {
  const { user } = useAuth();
  const ruta = rutaExpedienteAlertas((user?.permisos ?? []).map((p) => p?.name));
  return (
    <AlertasExpediente
      alertsAllEndpoint={API_CONFIG.ENDPOINTS.RECURSO_ALERTAS_ALL}
      rutas={{ gestion: ruta, consulta: ruta }}
      processName="Concesiones de Aguas"
      setToast={setToast}
      estadoNavegacion={estadoNavegacion}
    />
  );
}
