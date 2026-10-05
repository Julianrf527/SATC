import type { ModeloGenerico } from "@shared/types/common";
import type { Involucrado } from "@shared/types/involucrado";
import type { ActoAdministrativo } from "@shared/types/sancionatorio";

export type TipoAfectacion = {
  id: number;
  nombre: string;
  recurso_id: number;
};

export type Quejoso = {
  id: number;
  nombre: string | null;
  telefono: string | null;
  correo: string | null;
  anonimo: boolean;
};

export type Expediente = {
  id: number;
  radicado: string;
  fecha_radicado: string;
  municipio: ModeloGenerico;
  fecha_creacion: string;
  involucrados: Involucrado[];
  etapa_actual?: string | null;
  archivado: true | false;
  estado?: string | null;
};

export type ExpedienteDetalle = Expediente & {
  direccion: string;
  descripcion: string;
  vereda: ModeloGenerico;
  quejosos: Quejoso[];
  tipos_afectacion: TipoAfectacion[];
  recurso_afectado: ModeloGenerico[];
  radicados_asociados?: string[];
};

export type RespuestaData = {
  id: number;
  expediente_id: number;
  radicado: string;
  fecha_radicado: string;
  documento_radicado_id: number;
  requiere_medida_preventiva: boolean;
  fecha_creacion?: string;
};

// ── Etapas (respuesta, concepto, cierre) ──────────────────────────────────

export type TipoMedida = { id: number; nombre: string };

export type MedidaInfo = {
  tipo_medida_id: number;
  cantidad: string;
  especie: string;
  estado_medida: boolean | null;
  tipo_medidas: TipoMedida[];
};

export type MedidaPreventiva = {
  id: number;
  etapa_respuesta_id: number;
  acto_administrativo_id: number | null;
  informacion: MedidaInfo;
  /** Formato ActoAdmin-compatible (sancionatorio) que devuelve el backend. */
  acto_admin: ActoAdministrativo | null;
};

/** GET /etapas/respuesta/{expediente}: `null` cuando la etapa no existe (404). */
export type RespuestaEtapa = {
  respuesta: RespuestaData;
  medida: MedidaPreventiva | null;
};

export type TipoAcogidaConcepto = "AUTO_REQUERIMIENTO" | "OFICIO" | "RESOLUCION_ARCHIVO";

export type OficioRemite = {
  id: number;
  radicado: string;
  fecha_radicado: string;
  fecha_remitido: string;
  archivo_remite_id: number;
};

export type SolicitudInformacion = {
  id: number;
  radicado: string;
  fecha_radicado: string;
  archivo_solicitud_id: number;
};

export type ConceptoEtapaData = {
  id: number;
  expediente_id: number;
  tipo_acogida_concepto: TipoAcogidaConcepto;
  dias_termino: number | null;
  fecha_termino_calculada: string | null;
  acto_administrativo_id: number | null;
  fecha_creacion: string;
  acto_admin: ActoAdministrativo | null;
  oficio_remite: OficioRemite | null;
  solicitud_informacion: SolicitudInformacion | null;
};

export type CierreEtapaData = {
  id: number;
  expediente_id: number;
  acto_administrativo_id: number | null;
  fecha_creacion: string;
  acto_admin: ActoAdministrativo | null;
};

/**
 * Respuesta de GET de una etapa que puede no existir aún: `data` es `null`
 * con 404, y entonces `creable`/`creable_msg` dicen si se puede crear.
 */
export type EtapaConsulta<T> = {
  data: T | null;
  creable: boolean;
  creableMsg: string | null;
};

/** GET /expedientes/completo/{id} */
export type ExpedienteCompletoResponse = {
  data?: Partial<ExpedienteDetalle> | null;
  tipo_notificacion?: ModeloGenerico | null;
  etapas_existentes?: number[];
};

export type ModoInforme = "FLUJO" | "MANUAL";
export type TipoInforme = "VISITA" | "SEGUIMIENTO";

/**
 * Resumen del proceso de revisión vigente que el backend agrega a cada
 * informe en /informes, /informes/mios y la etapa (`resumen_proceso`).
 * `estado_proceso` ya viene con etiqueta y tono: no se mapea en el front.
 */
export type ResumenProcesoInforme = {
  proceso_id: number | null;
  estado_proceso: { codigo: string; etiqueta: string; tono: "info" | "success" | "warning" | "error" | "neutral" } | null;
  /** Hay proceso vigente y no está en un estado final. */
  proceso_activo: boolean;
  numero_devoluciones: number;
  version_actual: number;
  /** Al usuario actual le toca subir/revisar. */
  requiere_mi_accion: boolean;
};

/** Fila de GET /informes y `data` de GET /etapas/informe-tecnico/{exp}/{tipo}. */
export type InformeTecnico = ResumenProcesoInforme & {
  id: number;
  expediente_id: number;
  expediente_radicado?: string | null;
  profesional_asignado_id: number | null;
  profesional_nombre: string | null;
  revisor_asignado_id: number | null;
  revisor_nombre: string | null;
  fecha_programacion_visita: string | null;
  fecha_recibido_informe: string | null;
  fecha_aceptacion_informe: string | null;
  documento_informe_id: number | null;
  tipo_informe: string;
  fecha_creacion: string;
  aceptado: boolean;
  modo: ModoInforme;
  tiene_matriz?: boolean;
  recursos_afectados?: FilaRecursoAfectado[] | null;
};

/** Fila de GET /informes/mios. */
export type MiInforme = ResumenProcesoInforme & {
  id: number;
  expediente_id: number;
  expediente_radicado: string | null;
  tipo_informe: string;
  modo: ModoInforme;
  soy_profesional: boolean;
  soy_revisor: boolean;
  fecha_programacion_visita: string | null;
  fecha_recibido_informe: string | null;
  fecha_aceptacion_informe: string | null;
  documento_informe_id: number | null;
  aceptado: boolean;
  puede_diligenciar_matriz: boolean;
  tiene_matriz: boolean;
};

export const RECURSOS_MATRIZ = [
  "AIRE", "SUELO", "AGUA", "PAISAJE", "FLORA", "FAUNA", "RUIDO", "SOCIAL", "OTRO",
] as const;

export type RecursoMatriz = (typeof RECURSOS_MATRIZ)[number];

export type FilaRecursoAfectado = {
  recurso: RecursoMatriz;
  magnitud: "LEVE" | "MODERADO" | "GRAVE" | null;
  reversibilidad: "REVERSIBLE" | "IRREVERSIBLE" | null;
  no_existe: boolean;
};

export type ProfesionalDisponible = {
  id: number;
  nombre: string;
};
