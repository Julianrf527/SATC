// Contrato `ProcesoDetalle` del backend (satc_shared/review_process/schemas.py).
// Lo devuelven todos los flujos de revisión; cada app puede extenderlo con
// campos propios (el adapter tipa ese extra con el genérico `D`).
//
// `acciones_disponibles` y `subida_version` se calculan POR USUARIO en el
// backend y son la única fuente de verdad: la UI no deduce reglas del estado.

/** Tono visual que el backend asigna a estados y acciones. */
export type TonoProceso = "info" | "success" | "warning" | "error" | "neutral";

export type EstadoProceso = {
  codigo: string;
  etiqueta: string;
  tono: TonoProceso;
};

export type ArchivoProceso = {
  file_id: number | null;
  url: string | null;
  nombre: string | null;
  size: number | null;
};

export type RevisorProceso = {
  revisor_id: number;
  nombre: string | null;
  fecha_asignacion: string | null;
  notificado: boolean;
};

export type VersionProceso = {
  version_id: number;
  numero_version: number;
  archivo: ArchivoProceso;
  usuario_subida_id: number | null;
  comentario: string;
  fecha_subida: string | null;
};

export type RevisionProceso = {
  revision_id: number;
  revisor_id: number;
  revisor_nombre: string;
  accion: string;
  /** En participio ("Aprobado", "Devuelto", "Aprobado para firma"). */
  accion_etiqueta: string;
  tono: TonoProceso;
  comentarios: string;
  version_revisada: number | null;
  fecha_revision: string | null;
  adjunto: ArchivoProceso | null;
};

export type AuditoriaProceso = {
  auditoria_id: number;
  usuario_id: number | null;
  /** Código del evento (`crear`, `aprobar`, `aprobar_firma`...). */
  accion: string;
  /** Etiqueta del evento según el flujo del backend. */
  accion_etiqueta: string;
  tono: TonoProceso;
  descripcion: string;
  datos_adicionales: Record<string, unknown> | null;
  fecha_accion: string | null;
};

export type ReglaAdjunto = {
  permitido: boolean;
  extensiones: string[];
};

export type AccionDisponible = {
  codigo: string;
  /** Imperativo, para el botón ("Aprobar"). */
  etiqueta: string;
  tono: TonoProceso;
  requiere_comentario: boolean;
  /** Siempre presente: `permitido: false` si la acción no admite adjunto. */
  adjunto: ReglaAdjunto;
  /** Motivo si la acción aplica pero hoy no se puede ejecutar. */
  bloqueada: string | null;
  /** Ícono semántico ("aprobar", "devolver", "firmar"...); desconocido o null = sin ícono. */
  icono: string | null;
};

export type SubidaVersion = {
  permitida: boolean;
  extensiones: string[];
  motivo: string | null;
};

export type ProcesoDetalle = {
  id: number;
  nombre: string;
  descripcion: string;
  estado: EstadoProceso;
  version_actual: number;
  numero_devoluciones: number;
  max_devoluciones: number;
  creador_id: number;
  fecha_creacion: string | null;
  fecha_ultima_actualizacion: string | null;
  revisores: RevisorProceso[];
  /** Más reciente primero. */
  versiones: VersionProceso[];
  /** Más reciente primero. */
  revisiones: RevisionProceso[];
  /** Cronológica. */
  auditoria: AuditoriaProceso[];
  acciones_disponibles: AccionDisponible[];
  /** `null`: el usuario no sube versiones en este proceso. */
  subida_version: SubidaVersion | null;
};

/** Datos que el formulario de revisión entrega al adapter. */
export type DatosRevision = {
  accion: string;
  comentario: string;
  adjunto: File | null;
};

/** Datos que el formulario de subida entrega al adapter. */
export type DatosVersion = {
  archivo: File;
  comentario: string;
};

/**
 * Respuesta de una mutación (revisar / subir versión). Cada backend añade
 * campos propios (`numero_devoluciones`, `version`, ...); el módulo los lee
 * en `onCambio` si los necesita.
 */
export type ResultadoAccion = {
  ok: boolean;
  message?: string;
  [campo: string]: unknown;
};

/** Evento que recibe `onCambio` tras una mutación exitosa. */
export type CambioProceso = {
  tipo: "revision" | "version";
  resultado: ResultadoAccion;
};
