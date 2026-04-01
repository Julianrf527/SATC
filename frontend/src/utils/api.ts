// Configuración de la URL base del API
// En producción (Docker) usa window.ENV.VITE_API_URL inyectado en runtime (vacío = URLs relativas)
// En desarrollo usa import.meta.env.VITE_API_URL o vacío (proxy de Vite)
export const BASE_URL: string =
  (window as any).ENV?.VITE_API_URL ?? import.meta.env.VITE_API_URL ?? "";

export const API_CONFIG = {
  ENDPOINTS: {
    /*---Users api---*/
    /*auth route*/
    AUTH_LOGIN: "/users/auth/login",
    AUTH_RECOVERY: "/users/auth/recovery",
    AUTH_RECOVERY_CODE: "/users/auth/recovery-code",
    AUTH_ME: "/users/auth/me",
    AUTH_LOGOUT: "/users/auth/logout",
    /*user route*/
    USER_REGISTER: "/users/user/register",
    USERS: "/users/user/all",
    USER_TOGGLE_STATE: (user_id: number) =>
      `/users/user/toggleState/${user_id}`,
    USER_TOGGLE_ROLE: (user_id: number, rol_id: number) =>
      `/users/user/toggleRol/${user_id}/${rol_id}`,
    PASSWORD_RESET: "/users/user/password-resets",
    USER_UPDATE: "/users/user/update-user",
    USER_LOG: "/users/user/log",
    /*role route*/
    ROL_LIST: "/users/role/all",
    ROLES: "/users/role/all", // Alias para compatibilidad
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
    /*notification route*/
    NOTIFICATION_STREAM: "/users/notification/stream",
    NOTIFICATION_CREATE: "/users/notification/add",
    NOTIFICATION_DELETE: (noti_id: number) => `/users/notification/${noti_id}`,
    NOTIFICATION_DELETE_ALL: "/users/notification/delete-all",
    NOTIFICATION_LINKED: (linked_id: string) =>
      `/users/notification/linked/${linked_id}`,

    /*---Sancionatoria api---*/
    /*town route*/
    TOWNS_SIDEWALK: "/sanctioning/town/sidewalk",
    TOWNS_SIDEWALK_BY_TOWN: (town_id: number) =>
      `/sanctioning/town/sidewalk/${town_id}`,
    BUSINESS_DAYS: "/sanctioning/town/utils/business-days",

    INVOLVED_EXPEDIENTE_LINK: "/sanctioning/involved/involved-file",
    INVOLVED_EXPEDIENTE_UNLINK: (file_involved_id: number) =>
      `/sanctioning/involved/involved-file/${file_involved_id}`,
    EXPEDIENTE_INVOLVED_LIST: (file_id: string) =>
      `/sanctioning/involved/involved-list/${file_id}`,

    //file route*/
    FILES: "/sanctioning/file/get",
    FILE_FILTER: "/sanctioning/file/filter",
    FILE_AFFECTED_RESOURCE: "/sanctioning/file/affected-resource",
    FILES_VIEW: "/sanctioning/file/get/all",
    FILES_BY_USER: (user_id: number) => `/sanctioning/file/${user_id}`,
    FILE_ADD: "/sanctioning/file/add",
    FILE_UPDATE_ENCARGADO: (file_id: string, encargado_id?: number) =>
      `/sanctioning/file/${file_id}/charge/${encargado_id ?? ""}`,
    FILE_BULK_UPDATE_ENCARGADO: "/sanctioning/file/charge/bulk",
    FILE_ARCHIVE: (file_id: string) => `/sanctioning/file/${file_id}/archive`,
    AUDIT_LOGS: "/sanctioning/file/audit/logs",
    FILE_ALERTS: (file_id: string) => `/sanctioning/file/alerts/${file_id}`,
    FILE_ALERTS_ALL: "/sanctioning/file/alerts/all",
    FILE_DOWNLOAD_ALL: (file_id: string) =>
      `/sanctioning/file/download/${file_id}`,

    //stage route
    FILE_CREATE_STAGE: (file_id: string, type?: number) =>
      `/sanctioning/stage/${file_id}/stage/${type}`,
    FILE_FUll: (file_id: string) => `/sanctioning/stage/full/${file_id}`,
    FILE_BASIC_DATA: (file_id: string) =>
      `/sanctioning/stage/${file_id}/basic-data`,
    FILE_INVESTIGATION: (file_id: string) =>
      `/sanctioning/stage/investigation/${file_id}`,

    FILE_MEASURE: (file_id: string) => `/sanctioning/stage/measure/${file_id}`,
    FILE_MEASURE_CREATE: "/sanctioning/stage/measure",
    FILE_MEASURE_UPDATE: (medida_id: number) =>
      `/sanctioning/stage/measure/${medida_id}`,

    FILE_START_PROCESS: (file_id: string) =>
      `/sanctioning/stage/start-process/${file_id}`,

    FILE_CESSATION: (file_id: string) =>
      `/sanctioning/stage/cessation/${file_id}`,
    FILE_CESSATION_CREATE: "/sanctioning/stage/cessation",
    FILE_CESSATION_UPDATE: (cessation_id: number) =>
      `/sanctioning/stage/cessation/${cessation_id}`,

    FILE_FORMULATION: (file_id: string) =>
      `/sanctioning/stage/formulation/${file_id}`,
    FILE_FORMULATION_CREATE: "/sanctioning/stage/formulation",
    FILE_FORMULATION_UPDATE: (formulation_id: number) =>
      `/sanctioning/stage/formulation/${formulation_id}`,

    FILE_OPENING_PROBATIONARY: (file_id: string) =>
      `/sanctioning/stage/opening/${file_id}`,

    FILE_CLOSING_PROBATIONARY: (file_id: string) =>
      `/sanctioning/stage/closing/${file_id}`,

    FILE_DECISION: (file_id: string) =>
      `/sanctioning/stage/decision/${file_id}`,
    FILE_DECISION_CREATE: "/sanctioning/stage/decision",
    FILE_DECISION_UPDATE: (decision_id: number) =>
      `/sanctioning/stage/decision/${decision_id}`,

    FILE_RESOURCE: (file_id: string) =>
      `/sanctioning/stage/resource/${file_id}`,

    FILE_EXECUTION: (file_id: string) =>
      `/sanctioning/stage/execution/${file_id}`,
    FILE_EXECUTION_CREATE: "/sanctioning/stage/execution",
    FILE_EXECUTION_UPDATE: (ejecucion_id: number) =>
      `/sanctioning/stage/execution/${ejecucion_id}`,

    AUDIT_ETAPAS_BATCH: "/sanctioning/stage/audit/batch",

    //acto route
    FILE_ACTO_ADMIN: `/sanctioning/acto/acto-admin`,
    FILE_ACTO_ADMIN_UPDATE: (acto_id: number) =>
      `/sanctioning/acto/acto-admin/${acto_id}`,
    FILE_ACTO_ADMIN_DELETE: (acto_id: number) =>
      `/sanctioning/acto/acto-admin/${acto_id}`,

    FILE_COMUNICACION: "/sanctioning/acto/comunication",
    FILE_COMUNICACION_UPDATE: (comunicacion_id: number) =>
      `/sanctioning/acto/comunication/${comunicacion_id}`,
    FILE_COMUNICACION_DELETE: (comunicacion_id: number) =>
      `/sanctioning/acto/comunication/${comunicacion_id}`,

    FILE_NOTIFICACION: "/sanctioning/acto/notificacion",
    FILE_NOTIFICACION_DELETE: (notificacion_id: number) =>
      `/sanctioning/acto/notificacion/${notificacion_id}`,

    /*---- document api ----*/

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
    //document route
    FILE_UPLOAD: "/documents/files/upload",
    FILE: (file_id: number) => `/documents/files/${file_id}`,
    FILE_BATCH: "/documents/files/batch",
    FILE_DOWNLOAD: (file_id: number) => `/documents/files/download/${file_id}`,

    /* --- involved api --- */
    //involved route
    INVOLVED: (involved_id: number) => `/involveds/involved/${involved_id}`,
    INVOLVED_SEARCH: (tipo: string, numero: string, dv?: string) =>
      `/involveds/involved/search/${tipo}/${numero}${dv ? `?dv=${dv}` : ""}`,
    INVOLVED_CREATE: "/involveds/involved/new",
    INVOLVED_UPDATE: (involved_id: number) =>
      `/involveds/involved/${involved_id}`,
    INVOLVED_MANAGE: "/involveds/involved/manage",
    INVOLVED_LOG: "/involveds/involved/log",
  },
};

// Función para mostrar cierre
const showSessionExpiredToast = () => {
  console.warn("Sesión expirada");
};

export const apiCall = async (
  endpoint: string,
  options: RequestInit = {},
): Promise<any> => {
  // Preparar headers
  const headers: Record<string, string> = { ...options.headers } as Record<
    string,
    string
  >;

  // Solo agregar Content-Type si NO es FormData
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    credentials: "include",
    headers,
    ...options,
  });

  // Interceptar respuestas 401 ANTES de parsear el JSON
  if (response.status === 401) {
    if (window.location.pathname !== "/login") {
      showSessionExpiredToast();
      document.cookie =
        "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";

      setTimeout(() => {
        window.location.href = "/login";
      }, 500);
    }

    const data = await response
      .json()
      .catch(() => ({ detail: "Sesión expirada" }));

    return {
      ok: false,
      status: 401,
      unauthorized: true,
      ...data,
    };
  }

  // Para otras respuestas, parsear normalmente
  const data = await response.json().catch(() => ({}));

  return {
    ok: response.ok,
    status: response.status,
    ...data,
  };
};
