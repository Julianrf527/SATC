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
  /** Solo en "todas las alertas": el usuario es el responsable del expediente. */
  es_responsable?: boolean;
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
