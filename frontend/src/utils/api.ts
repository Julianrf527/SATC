import { toastService } from "./toastService";

// window.ENV lo inyecta docker-entrypoint.sh en runtime (no es parte del build de Vite).
declare global {
  interface Window {
    ENV?: { VITE_API_URL?: string };
  }
}

const RESOLVED_BASE_URL: string =
  window.ENV?.VITE_API_URL ?? import.meta.env.VITE_API_URL ?? "";
export const BASE_URL: string = RESOLVED_BASE_URL || window.location.origin;

export const API_CONFIG = {
  ENDPOINTS: {
    // ═══ Users API ═══
    // auth route
    AUTH_LOGIN: "/users/auth/login",
    AUTH_RECOVERY: "/users/auth/recovery",
    AUTH_RECOVERY_CODE: "/users/auth/recovery-code",
    AUTH_ME: "/users/auth/me",
    AUTH_LOGOUT: "/users/auth/logout",
    // user route
    USER_REGISTER: "/users/user/register",
    USERS: "/users/user/all",
    USER_TOGGLE_STATE: (user_id: number) =>
      `/users/user/toggleState/${user_id}`,
    USER_TOGGLE_ROLE: (user_id: number, rol_id: number) =>
      `/users/user/toggleRol/${user_id}/${rol_id}`,
    PASSWORD_CHANGE: "/users/user/password-change",
    USER_UPDATE: "/users/user/update-user",
    USER_LOG: "/users/user/log",
    // role route
    ROL_LIST: "/users/role/all",
    ROLES: "/users/role/all", // Alias de ROL_LIST
    PERMISSIONS: "/users/role/permissions",
    ROL_PERMISSIONS: "/users/role/role-permissions",
    VERIFY_PERMISSION: "/users/role/permission/verify",
    ROL_ADD: "/users/role/add",
    ROL_UPDATE: (rol_id: number | string) => `/users/role/update/${rol_id}`,
    ROL_DELETE: (rol_id: number | string) => `/users/role/delete/${rol_id}`,
    PERMISSION_ADD: "/users/role/permission/add",
    PERMISSION_UPDATE: (permission_id: string) =>
      `/users/role/permission/update/${permission_id}`,
    PERMISSION_DELETE: (permission_id: string) =>
      `/users/role/permission/delete/${permission_id}`,
    // notification route
    NOTIFICATION_STREAM: "/users/notification/stream",
    NOTIFICATION_CREATE: "/users/notification/add",
    NOTIFICATION_DELETE: (noti_id: number) => `/users/notification/${noti_id}`,
    NOTIFICATION_DELETE_ALL: "/users/notification/delete-all",
    NOTIFICATION_LINKED: (linked_id: string) =>
      `/users/notification/linked/${linked_id}`,

    // ═══ Sancionatoria API ═══
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

    // ═══ Document API ═══
    DOCS_LIST: "/documents/docs/list",
    DOCS_DETAIL: (documentId: number) => `/documents/docs/detail/${documentId}`,
    DOCS_CREATE: "/documents/docs/create",
    DOCS_UPLOAD_VERSION: (documentId: number) =>
      `/documents/docs/upload-version/${documentId}`,
    DOCS_REVIEW: (documentId: number) => `/documents/docs/review/${documentId}`,
    DOCS_DOWNLOAD: (versionId: number) =>
      `/documents/docs/download/${versionId}`,
    DOCS_STATS: "/documents/docs/stats",
    DOCS_REVIEWERS: "/documents/docs/reviewers",
    // document route
    FILE_UPLOAD: "/documents/files/upload",
    FILE: (file_id: number) => `/documents/files/${file_id}`,
    FILE_BATCH: "/documents/files/batch",
    FILE_DOWNLOAD: (file_id: number) => `/documents/files/download/${file_id}`,

    // ═══ Involved API ═══
    // involved route
    INVOLVED: (involved_id: number) => `/involveds/involved/${involved_id}`,
    INVOLVED_SEARCH: (tipo: string, numero: string, dv?: string) =>
      `/involveds/involved/search/${tipo}/${numero}${dv ? `?dv=${dv}` : ""}`,
    INVOLVED_CREATE: "/involveds/involved/new",
    INVOLVED_UPDATE: (involved_id: number) =>
      `/involveds/involved/${involved_id}`,
    INVOLVED_MANAGE: "/involveds/involved/manage",
    INVOLVED_LOG: "/involveds/involved/log",

    // ═══ Infraction API ═══
    // infraction route
    INFRACTIONS: "/infraction/file/get",
    INFRACTION_FILTER: "/infraction/file/filter",
    INFRACTION_AFFECTED_RESOURCE: "/infraction/file/affected-resource",
    INFRACTION_VIEW: "/infraction/file/get/all",
    INFRACTION_BY_USER: (user_id: number) => `/infraction/file/${user_id}`,
    INFRACTION_ADD: "/infraction/file/add",
    INFRACTION_UPDATE_ENCARGADO: (
      infraction_id: number,
      encargado_id?: number,
    ) => `/infraction/file/${infraction_id}/charge/${encargado_id ?? ""}`,
    INFRACTION_BULK_UPDATE_ENCARGADO: "/infraction/file/charge/bulk",
    INFRACTION_ARCHIVE: (infraction_id: number) =>
      `/infraction/file/${infraction_id}/archive`,
    INFRACTION_AUDIT_LOGS: "/infraction/file/audit/logs",
    INFRACTION_ALERTS: (infraction_id: number) =>
      `/infraction/file/alerts/${infraction_id}`,
    INFRACTION_ALERTS_ALL: "/infraction/file/alerts/all",
    INFRACTION_DOWNLOAD_ALL: (infraction_id: number) =>
      `/infraction/file/download/${infraction_id}`,
    INFRACTION_FUll: (infraction_id: number) =>
      `/infraction/file/full/${infraction_id}`,
    INFRACTION_BASIC_DATA: (infraction_id: number) =>
      `/infraction/file/${infraction_id}/basic-data`,
    INFRACTION_TIPOS_AFECTACION: "/infraction/file/tipos-afectacion",
    INFRACTION_COMPLAINER: "/infraction/file/complainer/list",
    INFRACTION_CREATE_COMPLAINER: "/infraction/file/complainer/add",
    // stage route
    INFRACTION_CREATE_ANSWER_STAGE: (expediente_id: number) =>
      `/infraction/stage/answer/${expediente_id}`,
    INFRACTION_GET_ANSWER: (expediente_id: number) =>
      `/infraction/stage/answer/${expediente_id}`,
    INFRACTION_PUT_ANSWER: (etapa_id: number) =>
      `/infraction/stage/answer/${etapa_id}`,
    INFRACTION_GET_REPORT: (expediente_id: number, tipo_informe: string) =>
      `/infraction/stage/technical-report/${expediente_id}/${tipo_informe}`,
    INFRACTION_MIGRATION_MEDIDA: (radicado: string) =>
      `/infraction/stage/migration/medida/${radicado}`,
    INFRACTION_CREATE_REPORT: (expediente_id: number, tipo_informe: string) =>
      `/infraction/stage/technical-report/${expediente_id}/create/${tipo_informe}`,
    INFRACTION_TIPO_MEDIDA: "/infraction/stage/tipo-medida",
    INFRACTION_CREATE_MEDIDA: (etapa_respuesta_id: number) =>
      `/infraction/stage/medida/${etapa_respuesta_id}`,
    INFRACTION_UPDATE_MEDIDA: (medida_id: number) =>
      `/infraction/stage/medida/${medida_id}`,
    // acto route
    INFRACTION_ACTO_ADMIN: "/infraction/acto/acto-admin",
    INFRACTION_ACTO_ADMIN_UPDATE: (acto_id: number) =>
      `/infraction/acto/acto-admin/${acto_id}`,
    INFRACTION_ACTO_ADMIN_DELETE: (acto_id: number) =>
      `/infraction/acto/acto-admin/${acto_id}`,
    INFRACTION_NOTIFICACION: "/infraction/acto/notificacion",
    INFRACTION_NOTIFICACION_UPDATE: (notificacion_id: number) =>
      `/infraction/acto/notificacion/${notificacion_id}`,
    INFRACTION_NOTIFICACION_DELETE: (notificacion_id: number) =>
      `/infraction/acto/notificacion/${notificacion_id}`,
    INFRACTION_TIPO_NOTIFICACION: "/infraction/acto/tipo-notificacion",
    INFRACTION_COMUNICACION: "/infraction/acto/comunicacion",
    INFRACTION_COMUNICACION_UPDATE: (id: number) =>
      `/infraction/acto/comunicacion/${id}`,
    INFRACTION_COMUNICACION_DELETE: (id: number) =>
      `/infraction/acto/comunicacion/${id}`,
    INFRACTION_GET_CIERRE: (expediente_id: number) =>
      `/infraction/stage/cierre/${expediente_id}`,
    INFRACTION_CREATE_CIERRE: (expediente_id: number) =>
      `/infraction/stage/cierre/${expediente_id}`,
    INFRACTION_GET_CONCEPTO: (expediente_id: number) =>
      `/infraction/stage/concepto/${expediente_id}`,
    INFRACTION_CREATE_CONCEPTO: (expediente_id: number) =>
      `/infraction/stage/concepto/${expediente_id}`,
    INFRACTION_PUT_CONCEPTO: (etapa_concepto_id: number) =>
      `/infraction/stage/concepto/${etapa_concepto_id}`,
    INFRACTION_CREATE_OFICIO_REMITE: (etapa_concepto_id: number) =>
      `/infraction/stage/oficio-remite/${etapa_concepto_id}`,
    INFRACTION_PUT_OFICIO_REMITE: (oficio_id: number) =>
      `/infraction/stage/oficio-remite/${oficio_id}`,
    INFRACTION_CREATE_SOLICITUD_INFO: (etapa_concepto_id: number) =>
      `/infraction/stage/solicitud-informacion/${etapa_concepto_id}`,
    INFRACTION_PUT_SOLICITUD_INFO: (solicitud_id: number) =>
      `/infraction/stage/solicitud-informacion/${solicitud_id}`,
    INFRACTION_DELETE_SOLICITUD_INFO: (solicitud_id: number) =>
      `/infraction/stage/solicitud-informacion/${solicitud_id}`,

    // involved route
    INFRACTION_INVOLVED_LINK: "/infraction/involved/involved-file",
    INFRACTION_INVOLVED_UNLINK: (infraction_involved_id: number) =>
      `/infraction/involved/involved-file/${infraction_involved_id}`,
    INFRACTION_INVOLVED_LIST: (infraction_id: number) =>
      `/infraction/involved/involved-list/${infraction_id}`,
    // town route
    INFRACTION_TOWNS_RURAL_DISTRICT: "/infraction/town/rural-district",
    INFRACTION_RURAL_DISTRICT_BY_TOWN: (municipio_id: number) =>
      `/infraction/town/rural-district/${municipio_id}`,

    // reports route
    INFRACTION_REPORTS_LIST: "/infraction/informes",
    INFRACTION_REPORTS_ASSIGN: (informe_id: number) =>
      `/infraction/informes/${informe_id}/assign`,
    INFRACTION_REPORTS_SYNC: (informe_id: number) =>
      `/infraction/informes/${informe_id}/sync`,
    INFRACTION_REPORTS_DOC_PROCESS: (informe_id: number) =>
      `/infraction/informes/${informe_id}/doc-process`,
  },
};

const showSessionExpiredToast = (message: string) => {
  toastService.showToast({
    id: Date.now(),
    message,
    type: "error",
  });
};

export const apiCall = async (
  endpoint: string,
  options: RequestInit = {},
): Promise<any> => {
  const headers: Record<string, string> = { ...options.headers } as Record<
    string,
    string
  >;

  // Con FormData el navegador debe fijar el Content-Type con su propio boundary.
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    credentials: "include",
    headers,
    ...options,
  });

  // Se intercepta antes del parseo genérico: el 401 dispara logout y redirección.
  if (response.status === 401) {
    const data = await response.json().catch(() => ({}));
    const yaEnLogin = window.location.pathname.startsWith("/login");

    document.cookie =
      "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";

    // Ya está viendo el login: recargar la misma página solo le tumba el
    // toast a medio mostrar sin aportar nada (no hay sesión que perder).
    if (!yaEnLogin) {
      if (data.detail === "session_replaced") {
        showSessionExpiredToast(
          "Tu sesión ha sido reemplazada por otro inicio de sesión. Si no fuiste tú, por favor cambia tu contraseña.",
        );
      } else {
        showSessionExpiredToast(
          "Tu sesión ha expirado. Por favor, inicia sesión nuevamente.",
        );
      }

      // Da tiempo a leer el toast antes de que el reload completo lo borre.
      setTimeout(() => {
        window.location.href = "/login";
      }, 2500);
    }

    return {
      ok: false,
      status: 401,
      unauthorized: true,
      ...data,
    };
  }

  // 403 se centraliza aquí para dar el mismo feedback en toda la app.
  if (response.status === 403) {
    const data = await response.json().catch(() => ({}));

    toastService.showToast({
      id: Date.now(),
      message:
        typeof data.detail === "string"
          ? data.detail
          : "No tienes permisos para realizar esta acción.",
      type: "error",
    });

    return {
      ok: false,
      status: 403,
      forbidden: true,
      ...data,
    };
  }

  // Evita falsos positivos cuando un proxy devuelve HTML (SPA fallback) con status 200.
  const contentType = response.headers.get("content-type") || "";
  if (response.status !== 204 && !contentType.includes("application/json")) {
    const raw = await response.text().catch(() => "");
    const detail =
      response.status === 503
        ? "Servicio temporalmente no disponible. Intente nuevamente."
        : response.status >= 500
          ? "Error interno del servidor. Intente nuevamente."
          : "Respuesta inesperada del servidor.";
    return {
      ok: false,
      status: response.status,
      detail,
      raw,
    };
  }

  const data = await response.json().catch(() => ({}));

  return {
    ok: response.ok,
    status: response.status,
    ...data,
  };
};

/** Extrae un mensaje legible de un valor atrapado en catch (tipo unknown). */
export function getErrorMessage(e: unknown, fallback = "Error desconocido"): string {
  return e instanceof Error && e.message ? e.message : fallback;
}

/**
 * Formatea el campo `detail` de una respuesta de error de FastAPI: string
 * simple, o array de errores de validación de Pydantic ([{msg, loc, ...}]).
 */
export function formatApiErrorDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((err) =>
        err && typeof err === "object" && "msg" in err
          ? String((err as { msg: unknown }).msg)
          : String(err),
      )
      .join(", ");
  }
  return fallback;
}
