export type EstadoSemaforo = "verde" | "amarillo" | "rojo" | "vencido";

export type Semaforo = {
  estado: EstadoSemaforo;
  color_hex: string;
  porcentaje_avance: number;
  urgencia: "baja" | "media" | "alta" | "critico";
  dias_transcurridos: number;
  dias_restantes: number;
  dias_totales: number;
  esta_vencido: boolean;
};

/** Rol responsable de una alerta: código de permiso y su nombre legible. */
export type RolResponsable = { permiso: string; etiqueta: string };

export type Alerta = {
  tipo: string;
  etapa: string;
  involucrado_nombre?: string;
  accion_requerida: string;
  plazo_legal: string;
  msg: string;
  fecha_inicio?: string;
  fecha_limite: string;
  semaforo: Semaforo;
  /** Solo en "todas las alertas": la alerta es del usuario (ver `roles_responsables`). */
  es_responsable?: boolean;
  /** Persona a cargo de la tarea (si la alerta no es por rol). */
  encargado_id?: number | null;
  /**
   * Roles a los que corresponde la alerta (p. ej. quienes deben revisar el
   * documento o quienes pueden asignar una visita). Si viene con elementos, la
   * alerta es de todo usuario con alguno de esos permisos; si no, del encargado.
   */
  roles_responsables?: RolResponsable[];
  /** Estado del documento de la tarea (informativo). */
  estado_documento?: string | null;
  /** app-recurso: expediente de la alerta (para abrirlo al navegar). */
  expediente_id?: number;
  /** app-recurso: proceso de revisión donde se hace la tarea (null si aún no existe). */
  proceso_id?: number | null;
};

/** Respuesta del endpoint de alertas de un expediente. */
export type AlertasExpedienteResponse = {
  alertas?: Record<string, Alerta>;
};

/** Respuesta clásica (sin `page`) del endpoint de alertas de todos los expedientes. */
export type AlertasTodasResponse = {
  ok: boolean;
  alcance?: "mios" | "todos";
  alertas: Record<string, Record<string, Alerta>>;
  total_expedientes: number;
  expedientes_con_alertas: number;
  estadisticas_semaforo: Record<EstadoSemaforo, number>;
};

/** Una alerta de la lista paginada (con su expediente y clave). */
export type AlertaPaginada = Alerta & {
  radicado: string;
  clave: string;
  es_responsable: boolean;
};

/** Respuesta del endpoint de alertas de todos los expedientes con `page`. */
export type AlertasPaginadasResponse = {
  ok: boolean;
  alcance: "mios" | "todos";
  /** Solo la página pedida, ordenada por urgencia y % de avance. */
  alertas: AlertaPaginada[];
  /** Alertas tras los filtros (todas las páginas). */
  total: number;
  page: number;
  limit: number;
  total_pages: number;
  total_expedientes: number;
  expedientes_con_alertas: number;
  /** Del alcance completo, sin filtros de radicado/estado/tipo. */
  estadisticas_semaforo: Record<EstadoSemaforo, number>;
  /** Tipos de alerta del alcance completo (para el selector). */
  tipos_disponibles: string[];
};

export type SetToast = (toast: {
  id: number;
  message: string;
  type: "success" | "error";
}) => void;
