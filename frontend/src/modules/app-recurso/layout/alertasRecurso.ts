import type { AlertaPaginada, DestinoAlerta } from "@features/alertas";
import type { EtapaTabId } from "../manage/etapasProceso";
import type { NavegacionExpediente } from "../types";

/**
 * Pestaña del expediente donde vive la tarea de cada alerta (claves de
 * app-recurso/services/alertas.py). El concepto adicional vive en
 * Requerimiento y el recurso de reposición en Decisión. "concepto_adicional_"
 * va antes que "concepto_" (el concepto de la etapa 2).
 */
const PESTANA_POR_PREFIJO: [string, EtapaTabId][] = [
  ["admite_", "auto-admite"],
  ["concepto_adicional_", "requerimiento"],
  ["concepto_", "concepto"],
  ["requerimiento_", "requerimiento"],
  ["decision_", "decision"],
  ["recurso_", "decision"],
];

export function pestanaDeAlerta(tipo: string): EtapaTabId {
  return PESTANA_POR_PREFIJO.find(([prefijo]) => tipo.startsWith(prefijo))?.[1] ?? "info";
}

export const RUTA_MIS_ACTUACIONES = "/recurso/my-reports";
const RUTA_GESTION = "/recurso/manage";
const RUTA_CONSULTA = "/recurso/consult";

/** Abre el expediente de la alerta por id, en la pestaña de su etapa. */
export function estadoExpedienteAlerta(alerta: AlertaPaginada): NavegacionExpediente {
  return { expedienteIdToSelect: alerta.expediente_id, pestanaToSelect: pestanaDeAlerta(alerta.tipo) };
}

/**
 * A dónde lleva el botón de una alerta (técnico y gestionar no van juntos en
 * un rol; si llegaran a ir, manda técnico):
 * - Técnico: si la tarea es suya y ya tiene proceso, "Actuación" abre ese
 *   proceso en Mis actuaciones; si no, Consulta del expediente.
 * - Gestionar: Gestionar (o Consultar si es de otro responsable), en la
 *   pantalla de gestión.
 * - Si no: Consulta del expediente.
 */
export function destinoAlertaRecurso(
  alerta: AlertaPaginada,
  permisos: Iterable<string | undefined>,
): DestinoAlerta {
  const tiene = new Set(permisos);
  const consulta: DestinoAlerta = { ruta: RUTA_CONSULTA, accion: "Consultar", estado: estadoExpedienteAlerta(alerta) };
  if (tiene.has("recurso_tecnico")) {
    if (alerta.es_responsable !== false && alerta.proceso_id) {
      return {
        ruta: RUTA_MIS_ACTUACIONES,
        accion: "Actuación",
        principal: true,
        title: "Abrir el proceso en Mis actuaciones",
        estado: { procesoIdToSelect: alerta.proceso_id },
      };
    }
    return consulta;
  }
  if (tiene.has("recurso_gestionar")) {
    return {
      ruta: RUTA_GESTION,
      accion: alerta.es_responsable === false ? "Consultar" : "Gestionar",
      estado: estadoExpedienteAlerta(alerta),
    };
  }
  return consulta;
}
