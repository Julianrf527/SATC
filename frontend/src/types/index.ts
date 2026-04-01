export interface Involved {
  id: number;
  numero_documento: number;
  digito_verificacion?: string | null;
  tipo_documento: string;
  nombre: string;
  celular: number;
  correo: string;
}

export type Resource = {
  id: number;
  name: string;
};

export type BasicFile = {
  radicado: string;
  nombre: string;
  fecha_creacion: string;
  direccion: string;
  municipio: Resource;
  involucrados: Involved[];
  ultima_etapa?: string | null;
  archivado: true | false;
};

export type File = BasicFile & {
  direccion: string;
  vereda: Resource;
  id_auxiliar?: number;
  recurso_afectado: number[];
  motivo_afectacion: string;
};

export type Sidewalk = {
  id: number;
  name: string;
};

export type Town = {
  id: number;
  name: string;
  sidewalk: { id: number; name: string }[];
};

export type Notifications = {
  id: number;
  involucrado_id: number;
  notificacion_id: number;
  numero_envio: string;
  fecha_envio: string;
  fecha_constancia: string;
  notificacion_exitosa: boolean;
};

export type TipoNotificacion = {
  id: number;
  nombre: string;
};

export type ProcesoNotificacion = {
  id: number;
  fechaCreacion: string;
  tipoNotificacionId: number;
  nombre: string;
  notificaciones: Notifications[];
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

export type ActoAdminData = {
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
