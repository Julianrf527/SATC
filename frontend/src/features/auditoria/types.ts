/** Registro de auditoría devuelto por los endpoints de logs de cada servicio. */
export type LogAuditoria = {
  id: number;
  usuario_id: number;
  usuario_nombre: string;
  usuario_documento?: string | null;
  usuario_correo: string;
  tabla_afectada: string;
  tipo_operacion: string;
  descripcion: string;
  expediente_radicado: string | null;
  id_registro: string | null;
  fecha: string;
  datos_anteriores: Record<string, unknown>;
  datos_nuevos: Record<string, unknown>;
};

/**
 * Endpoints de catálogos para traducir IDs -> nombre en el detalle. Roles y
 * permisos (app-users) y etapas (batch) se cargan siempre; el resto solo si
 * el módulo los indica.
 */
export type AuditMappingSources = {
  /** Municipios con `veredas` anidadas. */
  municipios?: string;
  recursos?: string;
  causas?: string;
  quejosos?: string;
};

/** Configuración que inyecta el módulo en la vista de logs. */
export type AuditLogConfig = {
  /** Nombre del query param para filtrar por documento del usuario. */
  documentoParam: string;
  /** Mostrar columna/filtro de radicado de expediente. */
  showRadicado: boolean;
  mappingSources: AuditMappingSources;
};

export type SetToast = (toast: {
  id: number;
  message: string;
  type: "success" | "error";
}) => void;
