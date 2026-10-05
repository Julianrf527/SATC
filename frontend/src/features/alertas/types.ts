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
};

/** Respuesta del endpoint de alertas de un expediente. */
export type AlertasExpedienteResponse = {
  alertas?: Record<string, Alerta>;
};

/** Respuesta del endpoint de alertas de todos los expedientes. */
export type AlertasTodasResponse = {
  ok: boolean;
  alertas: Record<string, Record<string, Alerta>>;
  total_expedientes: number;
  expedientes_con_alertas: number;
  estadisticas_semaforo: Record<EstadoSemaforo, number>;
};

export type SetToast = (toast: {
  id: number;
  message: string;
  type: "success" | "error";
}) => void;
