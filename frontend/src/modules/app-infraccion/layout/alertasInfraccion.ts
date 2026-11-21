import type { AlertaPaginada, DestinoAlerta } from "@features/alertas";
import type { CodigoEtapa } from "../manage/etapasProceso";

/** Alerta de app-infraction: las de informes técnicos traen su `informe_id`. */
export type AlertaInfraccion = AlertaPaginada & { informe_id?: number | null };

/**
 * Pestaña del expediente donde vive la tarea de cada alerta (claves de
 * app-infraction/services/alertas.py). "concepto_seguimiento_" va antes que
 * "concepto_" y que "seguimiento_"; el acto de la medida preventiva vive en
 * Respuesta.
 */
const PESTANA_POR_PREFIJO: [string, CodigoEtapa][] = [
  ["concepto_seguimiento_", "concepto_seguimiento"],
  ["concepto_", "concepto"],
  ["seguimiento_", "seguimiento"],
  ["visita_", "visita"],
  ["medida_", "respuesta"],
  ["respuesta_", "respuesta"],
  ["cierre_", "cierre"],
];

export function pestanaDeAlerta(tipo: string): CodigoEtapa {
  return PESTANA_POR_PREFIJO.find(([prefijo]) => tipo.startsWith(prefijo))?.[1] ?? "respuesta";
}

export const RUTA_MIS_ACTUACIONES = "/infraction/my-reports";
export const RUTA_ASIGNAR_INFORMES = "/infraction/reports";
const RUTA_GESTION = "/infraction/manage";
const RUTA_CONSULTA = "/infraction/consult";

const ASIGNAR_INFORMES = "infraccion_asignar_informes";
const LIDER_PROYECTO = "infraccion_lider_proyecto";

/** Abre el expediente de la alerta en la pestaña de su etapa (Gestionar / Consulta). */
export function estadoExpedienteAlerta(alerta: AlertaPaginada): Record<string, unknown> {
  return { radicadoToSelect: alerta.radicado, etapaToSelect: pestanaDeAlerta(alerta.tipo) };
}

/**
 * A dónde lleva el botón de una alerta, según de quién es AHORA
 * (`es_responsable`, `encargado_id`, `roles_responsables` del backend):
 * - Por rol "Asignar informes" (asignar la visita, o reasignarla tras agotar
 *   las devoluciones): "Asignar" abre Asignar informes filtrado por el radicado.
 * - Por rol "Líder de proyecto" (acto en revisión): "Actuación" abre el
 *   proceso del acto en Mis actuaciones.
 * - Del usuario y con informe técnico (técnico que debe cargar una versión,
 *   líder técnico que debe revisarla): "Actuación" abre el informe en Mis
 *   actuaciones.
 * - Del usuario y con infraccion_gestionar (abogado del expediente):
 *   "Gestionar", en la pestaña de la etapa.
 * - Si no: "Consultar" (o Gestionar en solo lectura para quien no tiene
 *   consultar; el backend solo le deja abrir los suyos).
 */
export function destinoAlertaInfraccion(
  alerta: AlertaInfraccion,
  permisos: Iterable<string | undefined>,
): DestinoAlerta {
  const tiene = new Set(permisos);
  const propia = alerta.es_responsable !== false;
  const roles = new Set((alerta.roles_responsables ?? []).map((r) => r.permiso));
  const expediente = estadoExpedienteAlerta(alerta);

  if (propia && roles.has(ASIGNAR_INFORMES) && tiene.has(ASIGNAR_INFORMES)) {
    return {
      ruta: RUTA_ASIGNAR_INFORMES,
      accion: "Asignar",
      principal: true,
      title: "Asignar profesional y fecha de la visita",
      estado: { expedienteRadicadoToFilter: alerta.radicado },
    };
  }
  if (propia && roles.has(LIDER_PROYECTO) && alerta.proceso_id) {
    return {
      ruta: RUTA_MIS_ACTUACIONES,
      accion: "Actuación",
      principal: true,
      title: "Revisar el acto en Mis actuaciones",
      estado: { actoProcesoIdToSelect: String(alerta.proceso_id) },
    };
  }
  if (propia && roles.size === 0 && alerta.informe_id) {
    return {
      ruta: RUTA_MIS_ACTUACIONES,
      accion: "Actuación",
      principal: true,
      title: "Abrir el informe técnico en Mis actuaciones",
      estado: { informeIdToSelect: String(alerta.informe_id) },
    };
  }
  if (propia && roles.size === 0 && tiene.has("infraccion_gestionar")) {
    return { ruta: RUTA_GESTION, accion: "Gestionar", estado: expediente };
  }
  if (!tiene.has("infraccion_consultar") && tiene.has("infraccion_gestionar")) {
    return { ruta: RUTA_GESTION, accion: "Consultar", estado: expediente };
  }
  return { ruta: RUTA_CONSULTA, accion: "Consultar", estado: expediente };
}
