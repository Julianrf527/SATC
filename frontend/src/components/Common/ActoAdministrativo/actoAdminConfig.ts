import { API_CONFIG } from "../../../utils/api";
import type { ActoAdministrativo } from "../../../types/sancionatorioApp";

/** Acto administrativo cargado, o `{}` cuando la etapa aún no tiene uno. */
// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export type ActoAdminOrEmpty = ActoAdministrativo | {};

export type TipoActo = "notificacion" | "comunicacion";

export type ActoAdminEndpoints = {
  actoAdmin: {
    create: string;
    update: (actoId: number) => string;
    delete: (actoId: number) => string;
  };
  notificacion: {
    base: string;
    delete: (notificacionId: number) => string;
  };
  comunicacion?: {
    create: string;
    update: (comunicacionId: number) => string;
    delete: (comunicacionId: number) => string;
  };
};

export type ActoAdminStageBinding = {
  type: string; // "etapa" | "etapa_concepto" | "etapa_cierre" | "medida_preventiva" | "etapa_san_*"
  id: number;
};

export const DEFAULT_ENDPOINTS: ActoAdminEndpoints = {
  actoAdmin: {
    create: API_CONFIG.ENDPOINTS.FILE_ACTO_ADMIN,
    update: API_CONFIG.ENDPOINTS.FILE_ACTO_ADMIN_UPDATE,
    delete: API_CONFIG.ENDPOINTS.FILE_ACTO_ADMIN_DELETE,
  },
  notificacion: {
    base: API_CONFIG.ENDPOINTS.FILE_NOTIFICACION,
    delete: API_CONFIG.ENDPOINTS.FILE_NOTIFICACION_DELETE,
  },
  comunicacion: {
    create: API_CONFIG.ENDPOINTS.FILE_COMUNICACION,
    update: API_CONFIG.ENDPOINTS.FILE_COMUNICACION_UPDATE,
    delete: API_CONFIG.ENDPOINTS.FILE_COMUNICACION_DELETE,
  },
};

export type SetToast = (toast: {
  id: number;
  message: string;
  type: "success" | "error";
}) => void;

export type ActoAdminSaveResult = { ok: boolean; error?: string };

export type ActoAdminFormData = {
  tipo_acto: string;
  numerado: string;
  fecha_numerado: string;
  documento_acto_id?: number;
  radicado_expediente: string;
  etapa_id: number;
  nivel_auxiliar?: boolean | null;
};

export type NotificacionFormData = {
  involucrado_id?: number;
  numerado: string;
  fecha_numerado: string;
  fecha_envio_citacion: string;
  fecha_constancia_citacion: string;
  notificacion_exitosa: boolean;
  tipo_notificacion_id?: number;
  fecha_notificacion?: string;
  documento_notificacion_id?: number;
  documento_citacion_id?: number;
};
