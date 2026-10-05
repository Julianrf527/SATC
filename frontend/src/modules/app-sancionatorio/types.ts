// Tipos del módulo app-sancionatorio. Lo compartido con otros módulos sigue en
// `@shared/types/sancionatorio` (Expediente, ActoAdministrativo, ...).
import type { ActoAdministrativo } from "@shared/types/sancionatorio";
import type { Involucrado } from "@shared/types/involucrado";

export type SetToast = (toast: {
  id: number;
  message: string;
  type: "success" | "error";
}) => void;

/** Catálogo simple {id, nombre} (tipos de medida, cesación, sanción). */
export type TipoCatalogo = { id: number; nombre: string };

/** Condición de creación de una etapa ({status:false, msg} bloquea). */
export type Creable = { status: boolean; msg?: string };

/** Acto administrativo tal como llega en la etapa (`{}` cuando no existe). */
export type ActoEtapa = ActoAdministrativo | Record<string, never>;

// ── Documentos anexos de etapa ───────────────────────────────────────────────

export type DocumentoAnexo = {
  id: number;
  nombre: string;
  documento_anexo_id: number;
  fecha_subida: string;
};

export type DocumentoAnexoPayload = {
  nombre: string;
  documento_anexo_id: number;
};

// ── Datos de etapa (GET /sanctioning/stage/<etapa>/<expediente>) ─────────────
// Contrato único (app-sancionatoria/routes/stage.py, "CONTRATO DE LAS ETAPAS"):
// {"<respuestaKey>": Etapa | null, "creable"?: Creable}. Los campos propios de
// cada etapa van planos, al mismo nivel que `etapa_id`.

/** Campos comunes a todas las etapas. */
export type EtapaBase = {
  id?: number | null;
  etapa_id?: number;
  acto_admin?: ActoEtapa | null;
  documentos_anexos?: DocumentoAnexo[];
};

/** Respuesta del GET de una etapa: datos (o `null` si no existe) + condición de creación. */
export type EtapaRespuesta<T> = { datos: T | null; creable: Creable | null };

export type EtapaFormulacion = EtapaBase & {
  descargos?: boolean | null;
  documento_id?: number | null;
};

export type EtapaCesacion = EtapaBase & {
  tipo_cesacion_id?: number | null;
};

export type EtapaMedida = EtapaBase & {
  tipo_medida_id?: number | null;
  cantidad?: string | null;
  especie?: string | null;
  estado_medida?: boolean | null;
};

export type EtapaDecision = EtapaBase & {
  tipo_sancion_id?: number | null;
  detalle?: string | null;
  /** Acto administrativo de recurso (acto auxiliar). */
  acto_recurso?: ActoEtapa | null;
  creable_acto_recurso?: Creable;
};

export type EtapaRecurso = EtapaBase & {
  /** Acto administrativo de decisión del recurso (acto auxiliar). */
  acto_decision?: ActoEtapa | null;
};

// ── Datos de formularios de etapa ────────────────────────────────────────────

export type Medida = {
  id: number;
  tipo_medida_id: number;
  cantidad: string;
  especie: string;
  estado_medida: boolean | null;
};

export type Cesacion = {
  id: number;
  tipo_cesacion_id: number;
};

export type Decision = {
  id: number;
  tipo_sancion_id: number;
  detalle: string;
};

export type FormulacionCargosInfo = {
  id: number;
  descargos: boolean | null;
  documento_id?: number | null;
};

/**
 * Datos de la ejecución de la sanción (body del POST/PUT y campos del GET).
 * `tipo_acto` = "AUTO" | "RES" + numerado de 4 dígitos (p. ej. "AUTO0123").
 */
export type EjecucionDatos = {
  tipo_acto: string;
  fecha_auto: string;
  documento_acto_administrativo_id: number | null;
  cobro_coactivo: boolean;
  documento_cobro_id: number | null;
  disposicion: boolean;
  ruia: boolean;
  documento_ruia_id: number | null;
  memorando: boolean;
  documento_memorando_id: number | null;
};

/** Ejecución registrada (con datos guardados) tal como la usan vista y formulario. */
export type Ejecucion = EjecucionDatos & { etapa_id: number };

export type EtapaEjecucion = EtapaBase & {
  [K in keyof EjecucionDatos]?: EjecucionDatos[K] | null;
};

export type TipoArchivoEjecucion = "cobro_coactivo" | "ruia" | "memorando" | "auto";

/** Datos migrables desde infracciones para crear la medida preventiva. */
export type MigracionMedida = {
  medida: {
    tipo_medida_id: number;
    cantidad: string;
    especie: string;
    estado_medida: boolean | null;
  };
  informe_tecnico_documento_id: number | null;
  acto: {
    tipo_acto: string;
    numerado: number;
    fecha_numerado: string | null;
    documento_acto_administrativo_id: number;
    comunicacion?: {
      numerado: number;
      fecha_numerado: string | null;
      fecha_envio: string | null;
      documento_comunicacion_id: number;
    } | null;
  } | null;
};

/** Respuesta de /sanctioning/stage/full/{id}. */
export type ExpedienteFullResponse = {
  data?: {
    involucrados?: Involucrado[];
    direccion?: string;
    vereda?: { id: number; nombre: string };
    ultima_etapa?: string | null;
    recurso_afectado?: (number | { id: number })[];
    motivo_afectacion?: string;
  } | null;
  tipo_notificacion?: TipoCatalogo | null;
  etapas_existentes?: number[];
};
