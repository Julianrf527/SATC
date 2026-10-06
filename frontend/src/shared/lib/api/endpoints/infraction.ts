// Endpoints del servicio app-infraction (/infraction).
// Strings fijos o funciones que construyen la ruta; se concatenan a BASE_URL en apiCall.
export const INFRACTION_ENDPOINTS = {
  // infraction route
  INFRACTIONS: "/infraction/expedientes",
  INFRACTION_FILTER: "/infraction/expedientes/filtrar",
  INFRACTION_AFFECTED_RESOURCE: "/infraction/expedientes/recursos-afectados",
  INFRACTION_VIEW: "/infraction/expedientes/todos",
  INFRACTION_BY_USER: (user_id: number) => `/infraction/expedientes/encargado/${user_id}`,
  INFRACTION_ADD: "/infraction/expedientes",
  INFRACTION_UPDATE_ENCARGADO: (
    infraction_id: number,
    encargado_id?: number,
  ) => `/infraction/expedientes/${infraction_id}/encargado/${encargado_id ?? ""}`,
  INFRACTION_BULK_UPDATE_ENCARGADO: "/infraction/expedientes/encargado/masivo",
  INFRACTION_ARCHIVE: (infraction_id: number) =>
    `/infraction/expedientes/${infraction_id}/archivar`,
  INFRACTION_AUDIT_LOGS: "/infraction/expedientes/auditoria/registros",
  INFRACTION_ALERTS: (infraction_id: number) =>
    `/infraction/expedientes/alertas/${infraction_id}`,
  INFRACTION_ALERTS_ALL: "/infraction/expedientes/alertas/todas",
  INFRACTION_DOWNLOAD_ALL: (infraction_id: number) =>
    `/infraction/expedientes/descargar/${infraction_id}`,
  INFRACTION_FUll: (infraction_id: number) =>
    `/infraction/expedientes/completo/${infraction_id}`,
  INFRACTION_BASIC_DATA: (infraction_id: number) =>
    `/infraction/expedientes/${infraction_id}/datos-basicos`,
  INFRACTION_RADICADO_INICIAL: (infraction_id: number) =>
    `/infraction/expedientes/${infraction_id}/radicado-inicial`,
  INFRACTION_TIPOS_AFECTACION: "/infraction/expedientes/tipos-afectacion",
  INFRACTION_COMPLAINER: "/infraction/expedientes/denunciantes",
  INFRACTION_CREATE_COMPLAINER: "/infraction/expedientes/denunciantes",
  // stage route
  INFRACTION_CREATE_ANSWER_STAGE: (expediente_id: number) =>
    `/infraction/etapas/respuesta/${expediente_id}`,
  INFRACTION_GET_ANSWER: (expediente_id: number) =>
    `/infraction/etapas/respuesta/${expediente_id}`,
  INFRACTION_PUT_ANSWER: (etapa_id: number) =>
    `/infraction/etapas/respuesta/${etapa_id}`,
  INFRACTION_GET_REPORT: (expediente_id: number, tipo_informe: string) =>
    `/infraction/etapas/informe-tecnico/${expediente_id}/${tipo_informe}`,
  INFRACTION_MIGRATION_MEDIDA: (radicado: string) =>
    `/infraction/etapas/migracion/medida/${radicado}`,
  INFRACTION_CREATE_REPORT: (expediente_id: number, tipo_informe: string) =>
    `/infraction/etapas/informe-tecnico/${expediente_id}/crear/${tipo_informe}`,
  INFRACTION_TIPO_MEDIDA: "/infraction/etapas/tipos-medida",
  INFRACTION_CREATE_MEDIDA: (etapa_respuesta_id: number) =>
    `/infraction/etapas/medidas/${etapa_respuesta_id}`,
  INFRACTION_UPDATE_MEDIDA: (medida_id: number) =>
    `/infraction/etapas/medidas/${medida_id}`,
  // acto route
  INFRACTION_ACTO_ADMIN: "/infraction/actos/administrativos",
  INFRACTION_ACTO_ADMIN_UPDATE: (acto_id: number) =>
    `/infraction/actos/administrativos/${acto_id}`,
  INFRACTION_ACTO_ADMIN_DELETE: (acto_id: number) =>
    `/infraction/actos/administrativos/${acto_id}`,
  INFRACTION_NOTIFICACION: "/infraction/actos/notificaciones",
  INFRACTION_NOTIFICACION_UPDATE: (notificacion_id: number) =>
    `/infraction/actos/notificaciones/${notificacion_id}`,
  INFRACTION_NOTIFICACION_DELETE: (notificacion_id: number) =>
    `/infraction/actos/notificaciones/${notificacion_id}`,
  INFRACTION_TIPO_NOTIFICACION: "/infraction/actos/tipos-notificacion",
  INFRACTION_COMUNICACION: "/infraction/actos/comunicaciones",
  INFRACTION_COMUNICACION_UPDATE: (id: number) =>
    `/infraction/actos/comunicaciones/${id}`,
  INFRACTION_COMUNICACION_DELETE: (id: number) =>
    `/infraction/actos/comunicaciones/${id}`,
  INFRACTION_GET_CIERRE: (expediente_id: number) =>
    `/infraction/etapas/cierre/${expediente_id}`,
  INFRACTION_CREATE_CIERRE: (expediente_id: number) =>
    `/infraction/etapas/cierre/${expediente_id}`,
  INFRACTION_GET_CONCEPTO: (expediente_id: number) =>
    `/infraction/etapas/concepto/${expediente_id}`,
  INFRACTION_CREATE_CONCEPTO: (expediente_id: number) =>
    `/infraction/etapas/concepto/${expediente_id}`,
  INFRACTION_PUT_CONCEPTO: (etapa_concepto_id: number) =>
    `/infraction/etapas/concepto/${etapa_concepto_id}`,
  INFRACTION_CREATE_OFICIO_REMITE: (etapa_concepto_id: number) =>
    `/infraction/etapas/oficio-remite/${etapa_concepto_id}`,
  INFRACTION_PUT_OFICIO_REMITE: (oficio_id: number) =>
    `/infraction/etapas/oficio-remite/${oficio_id}`,
  INFRACTION_CREATE_SOLICITUD_INFO: (etapa_concepto_id: number) =>
    `/infraction/etapas/solicitud-informacion/${etapa_concepto_id}`,
  INFRACTION_PUT_SOLICITUD_INFO: (solicitud_id: number) =>
    `/infraction/etapas/solicitud-informacion/${solicitud_id}`,
  INFRACTION_DELETE_SOLICITUD_INFO: (solicitud_id: number) =>
    `/infraction/etapas/solicitud-informacion/${solicitud_id}`,

  // involved route
  INFRACTION_INVOLVED_LINK: "/infraction/involucrados/vinculos",
  INFRACTION_INVOLVED_UNLINK: (infraction_involved_id: number) =>
    `/infraction/involucrados/vinculos/${infraction_involved_id}`,
  INFRACTION_INVOLVED_LIST: (infraction_id: number) =>
    `/infraction/involucrados/expediente/${infraction_id}`,
  // town route
  INFRACTION_TOWNS_RURAL_DISTRICT: "/infraction/municipios/veredas",
  INFRACTION_RURAL_DISTRICT_BY_TOWN: (municipio_id: number) =>
    `/infraction/municipios/veredas/${municipio_id}`,

  // reports route
  INFRACTION_REPORTS_LIST: "/infraction/informes",
  /** POST = asignar (409 si hay un proceso vigente sin terminar) · PUT = reasignar. */
  INFRACTION_REPORTS_ASIGNAR: (informe_id: number) =>
    `/infraction/informes/${informe_id}/asignar`,
  INFRACTION_REPORTS_CAMBIAR_MODO: (informe_id: number) =>
    `/infraction/informes/${informe_id}/cambiar-modo`,
  /** GET: etapas posteriores que el cambio de modo borraría en cascada. */
  INFRACTION_REPORTS_CAMBIAR_MODO_IMPACTO: (informe_id: number) =>
    `/infraction/informes/${informe_id}/cambiar-modo/impacto`,
  INFRACTION_REPORTS_CARGUE_MANUAL: (informe_id: number) =>
    `/infraction/informes/${informe_id}/cargue-manual`,
  INFRACTION_REPORTS_DISPONIBLES: "/infraction/informes/disponibles",
  INFRACTION_MIS_INFORMES: "/infraction/informes/mios",
  INFRACTION_INFORME_RECURSOS: (informe_id: number) =>
    `/infraction/informes/${informe_id}/recursos`,

  // revision-informes route (proceso de revisión propio del informe técnico)
  INFRACTION_REVISION_POR_INFORME: (informe_id: number) =>
    `/infraction/revision-informes/por-informe/${informe_id}`,
  INFRACTION_REVISION_DETALLE: (proceso_id: number) =>
    `/infraction/revision-informes/${proceso_id}`,
  INFRACTION_REVISION_REVISAR: (proceso_id: number) =>
    `/infraction/revision-informes/${proceso_id}/revisiones`,
  INFRACTION_REVISION_VERSIONES: (proceso_id: number) =>
    `/infraction/revision-informes/${proceso_id}/versiones`,
  INFRACTION_REVISION_DESCARGA_VERSION: (proceso_id: number, version_id: number) =>
    `/infraction/revision-informes/${proceso_id}/versiones/${version_id}/descarga`,
  INFRACTION_REVISION_ADJUNTO: (proceso_id: number, revision_id: number) =>
    `/infraction/revision-informes/${proceso_id}/revisiones/${revision_id}/adjunto`,
};
