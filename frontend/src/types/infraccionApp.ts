import type { ModeloGenerico } from "./common";
import type { Involucrado } from "./involucradoApp";

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

export type Notificacion = {
  id: number;
  involucrado_id: number;
  notificacion_id: number;
  numero_envio: string;
  fecha_envio: string;
  fecha_constancia: string;
  notificacion_exitosa: boolean;
};

export type ProcesoNotificacion = {
  id: number;
  fechaCreacion: string;
  tipoNotificacionId: number;
  nombre: string;
  notificaciones: Notificacion[];
};

export type InvolucradoNotificacion = {
  id: number;
  involucrado_id: number;
  numerado: string;
  fecha_numerado: string;
  fecha_envio_citacion: string;
  fecha_constancia_citacion: string | null;
  notificacion_exitosa: boolean;
  documento_notificacion_id: number | null;
  documento_citacion_id: number;
  tipo_notificacion_id: number | null;
  fecha_notificacion: string | null;
  fecha_creacion: string;
};

export type NotificacionData = {
  id: number;
  fecha_creacion: string;
  involucrados: InvolucradoNotificacion[];
};

export type ActoAdministrativo = {
  id: number;
  numerado: string;
  fecha_numerado: string;
  documento_acto_id: number;
  tipo_acto: string;
  fecha_creacion: string;
  etapa_id: number;
  nivel_auxiliar?: boolean | null;
  comunicacion?: {
    id: number;
    numerado: string;
    fecha_numerado: string;
    fecha_envio: string;
    fecha_creacion: string;
    documento_comunicacion_id: number;
  } | null;
  notificacion?: NotificacionData | null;
};

export type RespuestaData = {
  id: number;
  expediente_id: number;
  radicado: string;
  fecha_radicado: string;
  documento_radicado_id: number;
  requiere_medida_preventiva: boolean;
};

export type InformeTecnico = {
  id: number;
  expediente_id: number;
  expediente_radicado?: string | null;
  profesional_asignado_id: number | null;
  profesional_nombre: string | null;
  fecha_programacion_visita: string | null;
  fecha_recibido_informe: string | null;
  fecha_aceptacion_informe: string | null;
  documento_informe_id: number | null;
  tipo_informe: string;
  fecha_creacion: string;
  docs_documento_id: number | null;
  proceso_activo: boolean;
  aceptado: boolean;
};

export type ProfesionalDisponible = {
  id: number;
  nombre: string;
};
