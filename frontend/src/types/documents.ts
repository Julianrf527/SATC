export type EstadoDocumento =
  | "en_revision"
  | "aprobado"
  | "rechazado"
  | "finalizado";

export type TipoArchivo = "pdf" | "docx" | "doc";

export type AccionAuditoria =
  | "crear"
  | "subir_version"
  | "aprobar"
  | "devolver"
  | "asignar_revisor"
  | "finalizar";

export type EstadoRevision = "aprobado" | "devuelto";

export interface DocumentoResumen {
  id: number;
  nombre: string;
  descripcion: string | null;
  estado: EstadoDocumento;
  fecha_creacion: string;
  fecha_ultima_actualizacion: string;
  version_actual: number;
  numero_devoluciones: number;
  usuario_creador_id: number;
  total_revisiones: number;
  total_revisores: number;
}

export interface VersionDocumento {
  version_id: number;
  numero_version: number;
  archivo_url: string;
  archivo_nombre: string;
  archivo_size: number;
  fecha_subida: string;
  comentario: string | null;
}

export interface Revision {
  revision_id: number;
  revisor_id: number;
  estado: EstadoRevision;
  comentarios: string | null;
  fecha_revision: string;
  version_revisada: number;
}

export interface RevisorAsignado {
  revisor_id: number;
  fecha_asignacion: string;
  notificado: boolean;
}

export interface AuditoriaItem {
  auditoria_id: number;
  usuario_id: number;
  accion: AccionAuditoria;
  descripcion: string | null;
  fecha_accion: string;
}

export interface DocumentoCompleto {
  documento_id: number;
  nombre: string;
  descripcion: string | null;
  tipo_archivo: TipoArchivo;
  estado: EstadoDocumento;
  version_actual: number;
  numero_devoluciones: number;
  fecha_creacion: string;
  usuario_creador_id: number;
  versiones: VersionDocumento[];
  revisiones: Revision[];
  revisores_asignados: RevisorAsignado[];
  auditoria: AuditoriaItem[];
}

export interface DocumentoCreateData {
  nombre: string;
  descripcion?: string;
  tipo_archivo: TipoArchivo;
  usuario_creador_id: number;
  revisores_ids: number[];
  archivo: File;
}

export interface VersionUploadData {
  documento_id: number;
  usuario_id: number;
  comentario?: string;
  archivo: File;
}

export interface RevisionData {
  documento_id: number;
  revisor_id: number;
  estado_revision: EstadoRevision;
  comentarios?: string;
}

export interface EstadisticasCreador {
  total_creados: number;
  en_revision: number;
  aprobados: number;
  rechazados: number;
  finalizados: number;
}

export interface EstadisticasRevisor {
  total_asignados: number;
  pendientes: number;
  total_revisiones: number;
  aprobados: number;
  devueltos: number;
}

export interface EstadisticasUsuario {
  creador?: EstadisticasCreador;
  revisor?: EstadisticasRevisor;
}

export interface UsuarioRevisor {
  id: number;
  nombre: string;
  email?: string;
}

export interface PermisosDocumento {
  canCreate: boolean;
  canReview: boolean;
}
