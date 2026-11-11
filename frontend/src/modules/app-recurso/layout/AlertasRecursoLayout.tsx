import { AlertasExpediente, type AlertaPaginada } from "@features/alertas";
import { API_CONFIG } from "@shared/lib/api";
import type { NavegacionExpediente, SetToast } from "../types";
import type { EtapaTabId } from "../manage/etapasProceso";

/**
 * Pestaña Alertas (/recurso/alerts, `recurso_gestionar`): "Mías" son las
 * alertas en las que el usuario es el encargado; "Todos", todas. Las reglas y
 * plazos viven en el backend (app-recurso/services/alertas.py).
 *
 * En Gestionar se ven todos los expedientes, así que ambos enlaces van ahí;
 * se abre el expediente por id en la pestaña de la etapa de la alerta.
 */
function pestanaDeAlerta(tipo: string): EtapaTabId {
  if (tipo.startsWith("admite_")) return "auto-admite";
  if (tipo.startsWith("concepto_")) return "concepto";
  return "info";
}

function estadoNavegacion(alerta: AlertaPaginada): NavegacionExpediente {
  return { expedienteIdToSelect: alerta.expediente_id, pestanaToSelect: pestanaDeAlerta(alerta.tipo) };
}

export default function AlertasRecursoLayout({ setToast }: { setToast: SetToast }) {
  return (
    <AlertasExpediente
      alertsAllEndpoint={API_CONFIG.ENDPOINTS.RECURSO_ALERTAS_ALL}
      rutas={{ gestion: "/recurso/manage", consulta: "/recurso/manage" }}
      processName="Concesiones de Aguas"
      setToast={setToast}
      estadoNavegacion={estadoNavegacion}
    />
  );
}
