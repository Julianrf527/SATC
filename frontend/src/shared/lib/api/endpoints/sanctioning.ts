// Endpoints del servicio app-sanctioning (/sanctioning).
// Strings fijos o funciones que construyen la ruta; se concatenan a BASE_URL en apiCall.
export const SANCTIONING_ENDPOINTS = {
  // town route
  TOWNS_SIDEWALK: "/sanctioning/town/rural-district",
  TOWNS_SIDEWALK_BY_TOWN: (town_id: number) =>
    `/sanctioning/town/rural-district/${town_id}`,
  BUSINESS_DAYS: "/sanctioning/town/utils/business-days",
  // involved route
  FILE_INVOLVED_LINK: "/sanctioning/involved/involved-file",
  FILE_INVOLVED_UNLINK: (file_involved_id: number) =>
    `/sanctioning/involved/involved-file/${file_involved_id}`,
  FILE_INVOLVED_LIST: (file_id: number) =>
    `/sanctioning/involved/involved-list/${file_id}`,

  // file route
  FILES: "/sanctioning/expediente/get",
  FILE_FILTER: "/sanctioning/expediente/filter",
  FILE_AFFECTED_RESOURCE: "/sanctioning/expediente/affected-resource",
  FILES_VIEW: "/sanctioning/expediente/get/all",
  FILES_BY_USER: (user_id: number) => `/sanctioning/expediente/${user_id}`,
  FILE_ADD: "/sanctioning/expediente/add",
  FILE_UPDATE_ENCARGADO: (file_id: number, encargado_id?: number) =>
    `/sanctioning/expediente/${file_id}/charge/${encargado_id ?? ""}`,
  FILE_BULK_UPDATE_ENCARGADO: "/sanctioning/expediente/charge/bulk",
  FILE_ARCHIVE: (file_id: number) => `/sanctioning/expediente/${file_id}/archive`,
  FILE_AUDIT_LOGS: "/sanctioning/expediente/audit/logs",
  FILE_ALERTS: (file_id: number) => `/sanctioning/expediente/alerts/${file_id}`,
  FILE_ALERTS_ALL: "/sanctioning/expediente/alerts/all",
  FILE_DOWNLOAD_ALL: (file_id: number) =>
    `/sanctioning/expediente/download-all/${file_id}`,
  FILE_FUll: (file_id: number) => `/sanctioning/stage/full/${file_id}`,
  FILE_BASIC_DATA: (file_id: number) =>
    `/sanctioning/expediente/${file_id}/basic-data`,

  // stage route
  // Cada etapa tiene su propio endpoint — no hay tipo_etapa_id
  FILE_INVESTIGATION: (expediente_id: number) =>
    `/sanctioning/stage/investigation/${expediente_id}`,
  FILE_INVESTIGATION_CREATE: (expediente_id: number) =>
    `/sanctioning/stage/investigation/${expediente_id}`,

  FILE_TIPO_MEDIDA: "/sanctioning/stage/measure-type",
  FILE_TIPO_CESACION: "/sanctioning/stage/cessation-type",
  FILE_TIPO_SANCION: "/sanctioning/stage/sanction-type",
  FILE_MEASURE: (expediente_id: number) =>
    `/sanctioning/stage/measure/${expediente_id}`,
  FILE_MEASURE_CREATE: (expediente_id: number) =>
    `/sanctioning/stage/measure/${expediente_id}`,
  FILE_MEASURE_UPDATE: (expediente_id: number) =>
    `/sanctioning/stage/measure/${expediente_id}`,

  FILE_START_PROCESS: (expediente_id: number) =>
    `/sanctioning/stage/start-process/${expediente_id}`,
  FILE_START_PROCESS_CREATE: (expediente_id: number) =>
    `/sanctioning/stage/start-process/${expediente_id}`,

  FILE_CESSATION: (expediente_id: number) =>
    `/sanctioning/stage/cessation/${expediente_id}`,
  FILE_CESSATION_CREATE: (expediente_id: number) =>
    `/sanctioning/stage/cessation/${expediente_id}`,
  FILE_CESSATION_UPDATE: (expediente_id: number) =>
    `/sanctioning/stage/cessation/${expediente_id}`,

  FILE_FORMULATION: (expediente_id: number) =>
    `/sanctioning/stage/formulation/${expediente_id}`,
  FILE_FORMULATION_CREATE: (expediente_id: number) =>
    `/sanctioning/stage/formulation/${expediente_id}`,
  FILE_FORMULATION_UPDATE: (expediente_id: number) =>
    `/sanctioning/stage/formulation/${expediente_id}`,

  FILE_OPENING_PROBATIONARY: (expediente_id: number) =>
    `/sanctioning/stage/opening/${expediente_id}`,
  FILE_OPENING_PROBATIONARY_CREATE: (expediente_id: number) =>
    `/sanctioning/stage/opening/${expediente_id}`,

  FILE_CLOSING_PROBATIONARY: (expediente_id: number) =>
    `/sanctioning/stage/closing/${expediente_id}`,
  FILE_CLOSING_PROBATIONARY_CREATE: (expediente_id: number) =>
    `/sanctioning/stage/closing/${expediente_id}`,

  FILE_DECISION: (expediente_id: number) =>
    `/sanctioning/stage/decision/${expediente_id}`,
  FILE_DECISION_CREATE: (expediente_id: number) =>
    `/sanctioning/stage/decision/${expediente_id}`,
  FILE_DECISION_UPDATE: (expediente_id: number) =>
    `/sanctioning/stage/decision/${expediente_id}`,

  FILE_RESOURCE: (expediente_id: number) =>
    `/sanctioning/stage/resource/${expediente_id}`,
  FILE_RESOURCE_CREATE: (expediente_id: number) =>
    `/sanctioning/stage/resource/${expediente_id}`,

  FILE_EXECUTION: (expediente_id: number) =>
    `/sanctioning/stage/execution/${expediente_id}`,
  FILE_EXECUTION_CREATE: (expediente_id: number) =>
    `/sanctioning/stage/execution/${expediente_id}`,
  FILE_EXECUTION_UPDATE: (expediente_id: number) =>
    `/sanctioning/stage/execution/${expediente_id}`,

  AUDIT_ETAPAS_BATCH: "/sanctioning/stage/audit/batch",

  // acto route
  FILE_ACTO_ADMIN: `/sanctioning/acto/acto-admin`,
  FILE_ACTO_ADMIN_UPDATE: (acto_id: number) =>
    `/sanctioning/acto/acto-admin/${acto_id}`,
  FILE_ACTO_ADMIN_DELETE: (acto_id: number) =>
    `/sanctioning/acto/acto-admin/${acto_id}`,

  FILE_COMUNICACION: "/sanctioning/acto/communication",
  FILE_COMUNICACION_UPDATE: (comunicacion_id: number) =>
    `/sanctioning/acto/communication/${comunicacion_id}`,
  FILE_COMUNICACION_DELETE: (comunicacion_id: number) =>
    `/sanctioning/acto/communication/${comunicacion_id}`,

  FILE_NOTIFICACION: "/sanctioning/acto/notificacion",
  FILE_NOTIFICACION_DELETE: (notificacion_id: number) =>
    `/sanctioning/acto/notificacion/${notificacion_id}`,

  FILE_POST_DOC_ATTACHED: (etapa_id: number) =>
    `/sanctioning/stage/doc-attached/${etapa_id}`,
  FILE_PUT_DOC_ATTACHED: (etapa_id: number, documento_id: number) =>
    `/sanctioning/stage/doc-attached/${etapa_id}/${documento_id}`,
  FILE_DELETE_DOC_ATTACHED: (etapa_id: number, documento_id: number) =>
    `/sanctioning/stage/doc-attached/${etapa_id}/${documento_id}`,
};
