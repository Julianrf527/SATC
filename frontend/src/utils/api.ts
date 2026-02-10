const BASE_URL = import.meta.env.VITE_API_URL;

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
    USER_TOGGLE_STATE: (id: number) => `/users/user/toggleState/${id}`,
    USER_TOGGLE_ROLE: (id: number, newRol: number) =>
      `/users/user/toggleRol/${id}/${newRol}`,
    PASSWORD_RESET: "/users/user/password-resets",
    USER_UPDATE: "/users/user/update-user",
    USER_LOG: "/users/user/log",
    /*role route*/
    ROLES: "/users/role/all",
    ROL_LIST: "/users/role/all",
    PERMISSIONS: "/users/role/permissions",
    ROL_PERMISSIONS: "/users/role/role-permissions",
    VERIFY_PERMISSION: "/users/role/permission/verify",

    ROL_ADD: "/users/role/add",
    ROL_UPDATE: (id: number | string) => `/users/role/update/${id}`,
    ROL_DELETE: (id: number | string) => `/users/role/delete/${id}`,
    PERMISSION_ADD: "/users/role/permission/add",
    PERMISSION_UPDATE: (id: string) => `/users/role/permission/update/${id}`,
    PERMISSION_DELETE: (id: string) => `/users/role/permission/delete/${id}`,
    /*notification route*/
    NOTIFICATION: (id_user: number) => `/users/notification/all/${id_user}`,
    NOTIFICATION_CREATE: "/users/notification/add",
    NOTIFICATION_DELETE: (id_noti: number) => `/users/notification/${id_noti}`,
    NOTIFICATION_DELETE_ALL: (userId: number) =>
      `/users/notification/user/${userId}`,
    NOTIFICATION_LINKED: (id_linked: string) =>
      `/users/notification/linked/${id_linked}`,
    /*---Sancionatoria api---*/
    /*town route*/
    TOWNS_SIDEWALK: "/sanctioning/town/sidewalk",
    TOWNS_SIDEWALK_BY_TOWN: (municipio_id: number) =>
      `/sanctioning/town/sidewalk/${municipio_id}`,
    BUSINESS_DAYS: "/sanctioning/town/utils/business-days",
    /*involved route*/
    INVOLVED_SEARCH: (numeroDocumento: string, tipoDocumento: string) =>
      `/sanctioning/involved/${numeroDocumento}/${tipoDocumento}`,
    INVOLVED_CREATE: "/sanctioning/involved/new",
    INVOLVED_UPDATE: (numeroDocumento: string, tipoDocumento: string) =>
      `/sanctioning/involved/${numeroDocumento}/${tipoDocumento}`,
    INVOLVED_MANAGE: "/sanctioning/involved/manage",
    INVOLVED_EDIT: (id: number) => `/sanctioning/involved/manage/${id}`,
    INVOLVED_EXPEDIENTE_LINK: "/sanctioning/involved/involved-file",
    INVOLVED_EXPEDIENTE_UNLINK: (
      radicado: string,
      numeroDocumento: number,
      tipoDocumento: string
    ) =>
      `/sanctioning/involved/involved-file/${radicado}/${numeroDocumento}/${tipoDocumento}`,
    EXPEDIENTE_INVOLVED_LIST: (radicado: string) =>
      `/sanctioning/involved/file/${radicado}`,
    /*documento route*/
    FILE_DOCUMENTO: "/sanctioning/document/new",
    FILE_DOCUMENTO_UPDATE: (id: number) => `/sanctioning/document/${id}`,
    FILE_DOCUMENTO_DELETE: (id: number) => `/sanctioning/document/${id}`,
    FILE_DOWNLOAD: (filePath: string) =>
      `/sanctioning/document/download?file_path=${encodeURIComponent(
        filePath
      )}`,
    /*file route*/
    FILE_CREATE_STAGE: (radicado: string, type?: number) =>
      `/sanctioning/file/${radicado}/stage/${type}`,

    FILES: "/sanctioning/file/get",
    FILE_FILTER: "/sanctioning/file/filter",
    FILE_AFFECTED_RESOURCE: "/sanctioning/file/affected-resource",
    FILES_VIEW: "/sanctioning/file/get/all",
    FILES_BY_USER: (userId: number) => `/sanctioning/file/${userId}`,
    FILE_ADD: "/sanctioning/file/add",
    FILE_UPDATE_ENCARGADO: (radicado: string, encargadoId?: number) =>
      `/sanctioning/file/${radicado}/encargado/${encargadoId ?? ""}`,

    FILE_FUll: (radicado: string) => `/sanctioning/file/full/${radicado}`,
    FILE_BASIC_DATA: (radicado: string) =>
      `/sanctioning/file/${radicado}/basic-data`,
    FILE_INVESTIGATION: (radicado: string) =>
      `/sanctioning/file/investigation/${radicado}`,

    FILE_MEASURE: (radicado: string) => `/sanctioning/file/measure/${radicado}`,
    FILE_MEASURE_CREATE: "/sanctioning/file/measure",
    FILE_MEASURE_UPDATE: (medida_id: number) =>
      `/sanctioning/file/measure/${medida_id}`,

    FILE_START_PROCESS: (radicado: string) =>
      `/sanctioning/file/start-process/${radicado}`,

    FILE_CESSATION: (radicado: string) =>
      `/sanctioning/file/cessation/${radicado}`,
    FILE_CESSATION_CREATE: "/sanctioning/file/cessation",
    FILE_CESSATION_UPDATE: (cessation_id: number) =>
      `/sanctioning/file/cessation/${cessation_id}`,

    FILE_FORMULATION: (radicado: string) =>
      `/sanctioning/file/formulation/${radicado}`,
    FILE_FORMULATION_CREATE: "/sanctioning/file/formulation",
    FILE_FORMULATION_UPDATE: (formulation_id: number) =>
      `/sanctioning/file/formulation/${formulation_id}`,

    FILE_OPENING_PROBATIONARY: (radicado: string) =>
      `/sanctioning/file/opening/${radicado}`,

    FILE_CLOSING_PROBATIONARY: (radicado: string) =>
      `/sanctioning/file/closing/${radicado}`,

    FILE_DECISION: (radicado: string) =>
      `/sanctioning/file/decision/${radicado}`,
    FILE_DECISION_CREATE: "/sanctioning/file/decision",
    FILE_DECISION_UPDATE: (decision_id: number) =>
      `/sanctioning/file/decision/${decision_id}`,

    FILE_RESOURCE: (radicado: string) =>
      `/sanctioning/file/resource/${radicado}`,

    FILE_EXECUTION: (radicado: string) =>
      `/sanctioning/file/execution/${radicado}`,
    FILE_EXECUTION_CREATE: "/sanctioning/file/execution",
    FILE_EXECUTION_UPDATE: (ejecucion_id: number) =>
      `/sanctioning/file/execution/${ejecucion_id}`,
    FILE_ARCHIVE: (radicado: string) =>
      `/sanctioning/file/${radicado}/archive`,

    FILE_ACTO_ADMIN: `/sanctioning/file/acto-admin`,
    FILE_ACTO_ADMIN_UPDATE: (id: number) =>
      `/sanctioning/file/acto-admin/${id}`,
    FILE_ACTO_ADMIN_DELETE: (id: number) =>
      `/sanctioning/file/acto-admin/${id}`,

    FILE_COMUNICACION: "/sanctioning/file/comunicacion",
    FILE_COMUNICACION_UPDATE: (id: number) =>
      `/sanctioning/file/comunicacion/${id}`,
    FILE_COMUNICACION_DELETE: (id: number) =>
      `/sanctioning/file/comunicacion/${id}`,

    FILE_NOTIFICACION: "/sanctioning/file/notificacion",
    FILE_NOTIFICACION_DELETE: (notificacionId: number) =>
      `/sanctioningfile//notificacion/${notificacionId}`,

    FILE_INVOLUCRADO_NOTIFICACION: "/sanctioning/file/involucrado-notificacion",
    FILE_INVOLUCRADO_NOTIFICACION_UPDATE: (invNotId: number) =>
      `/sanctioning/file/involucrado-notificacion/${invNotId}`,
    FILE_INVOLUCRADO_NOTIFICACION_DELETE: (invNotId: number) =>
      `/sanctioning/file/involucrado-notificacion/${invNotId}`,

    AUDIT_LOGS: "/sanctioning/file/audit/logs",
    AUDIT_ETAPAS_BATCH: "/sanctioning/file/audit/etapas/batch",

    FILE_ALERTS: (radicado: string) => `/sanctioning/file/alerts/${radicado}`,
    FILE_ALERTS_ALL: "/sanctioning/file/alerts/all",

    /*document route*/
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
  },
};

// Función para mostrar cierre
const showSessionExpiredToast = () => {
  console.warn("Sesión expirada");
};

export const apiCall = async (
  endpoint: string,
  options: RequestInit = {}
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
