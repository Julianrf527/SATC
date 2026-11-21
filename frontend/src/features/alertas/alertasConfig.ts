import { parseDate } from "@shared/lib/format";

/** Etiquetas cortas de los tipos de alerta (claves de ambos servicios). */
export const TIPO_LABELS: Record<string, string> = {
  inicio_sancionatorio: "Inicio Sancionatorio",
  decision_fondo: "Decisión de Fondo",
  presentacion_descargos: "Descargos",
  informe_tecnico: "Informe Técnico",
  alegato_conclusion: "Alegato",
  presentacion_recurso: "Recurso",
  resolucion_recurso: "Resolución",
  notificacion_recurso: "Notificación",
  respuesta_plazo: "Plazo Respuesta",
  concepto_constancia: "Constancia Citación",
  concepto_termino: "Término Concepto",
  concepto_seguimiento_constancia: "Constancia Citación (seguimiento)",
  concepto_seguimiento_termino: "Término Concepto seguimiento",
  visita_asignar: "Asignar visita técnica",
  visita_primera_version: "Concepto técnico: 1.ª versión",
  visita_aprobacion: "Concepto técnico: aprobación",
  seguimiento_asignar: "Asignar visita de seguimiento",
  seguimiento_primera_version: "Concepto de seguimiento: 1.ª versión",
  seguimiento_aprobacion: "Concepto de seguimiento: aprobación",
  concepto_solicitud: "Respuesta solicitud de información",
  concepto_acto_proyectar: "Auto de requerimiento: proyectar",
  concepto_acto_aprobacion: "Auto de requerimiento: aprobación",
  concepto_seguimiento_solicitud: "Respuesta solicitud de información (seguimiento)",
  concepto_seguimiento_acto_proyectar: "Auto de requerimiento seguimiento: proyectar",
  concepto_seguimiento_acto_aprobacion: "Auto de requerimiento seguimiento: aprobación",
  medida_acto_proyectar: "Acto medida preventiva: proyectar",
  medida_acto_aprobacion: "Acto medida preventiva: aprobación",
  cierre_acto_proyectar: "Acto de cierre: proyectar",
  cierre_acto_aprobacion: "Acto de cierre: aprobación",
  // Concesiones de Aguas (app-recurso)
  admite_primera_version: "Auto admite: 1.ª versión",
  admite_revision: "Auto admite: revisión",
  admite_version_final: "Auto admite: versión final",
  admite_aviso_publicado: "Aviso publicado",
  concepto_primera_version: "Concepto: 1.ª versión",
  concepto_version_final: "Concepto: versión final",
  requerimiento_primera_version: "Requerimiento: 1.ª versión",
  requerimiento_revision: "Requerimiento: revisión",
  requerimiento_version_final: "Requerimiento: versión final",
  concepto_adicional_tecnico: "Concepto adicional: técnico",
  concepto_adicional_primera_version: "Concepto adicional: 1.ª versión",
  concepto_adicional_revision: "Concepto adicional: revisión",
  concepto_adicional_version_final: "Concepto adicional: versión final",
  decision_primera_version: "Decisión: 1.ª versión",
  decision_revision: "Decisión: revisión",
  decision_version_final: "Decisión: versión final",
  recurso_acto: "Recurso: acto",
  recurso_concepto_pruebas: "Recurso: concepto de pruebas",
  recurso_acto_tras_pruebas: "Recurso: acto tras pruebas",
};

export const URGENCIA_ORDER: Record<string, number> = { critico: 0, alta: 1, media: 2, baja: 3 };

/**
 * Fecha corta es-CO ("5 ene." / "5 ene. 2026"). Usa `parseDate` para que las
 * fechas sin hora no se muestren un día antes (new Date("aaaa-mm-dd") es UTC).
 */
export function formatFechaCorta(f: string, withYear = false): string {
  const d = parseDate(f);
  if (!d) return f;
  return d.toLocaleDateString("es-CO", {
    ...(withYear ? { year: "numeric" } : {}),
    month: "short",
    day: "numeric",
  });
}
