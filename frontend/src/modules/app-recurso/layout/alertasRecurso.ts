import type { EtapaTabId } from "../manage/etapasProceso";

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

/**
 * A dónde lleva el clic de una alerta: Gestionar si el usuario gestiona; si
 * solo consulta (p. ej. un técnico), Consulta. Las dos usan la misma pantalla
 * y abren la pestaña pedida.
 */
export function rutaExpedienteAlertas(permisos: Iterable<string | undefined>): string {
  return new Set(permisos).has("recurso_gestionar") ? "/recurso/manage" : "/recurso/consult";
}
