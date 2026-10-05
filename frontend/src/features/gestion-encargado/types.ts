export type ExpedienteEncargado = {
  id: number;
  radicado: string;
  nombre_expediente: string;
  fecha_creacion: string;
  encargado_id: number | null;
  encargado_nombre?: string;
  encargado_documento?: string | number;
};

export type UsuarioEncargado = {
  id: number;
  nombre: string;
  numero_documento?: string | number;
};

export type RespuestaExpedientes = {
  ok: boolean;
  data: ExpedienteEncargado[];
  usuarios_disponibles: UsuarioEncargado[];
  page: number;
  limit: number;
  totalCount: number;
};

/** Endpoints que inyecta cada módulo. */
export type GestionEncargadoEndpoints = {
  lista: string;
  bulkUpdate: string;
};

export type ExpedientesEncargadoFiltros = {
  page: number;
  limit: number;
  radicado: string;
  nombreExpediente: string;
  fechaCreacion: string;
};

export type SetToast = (toast: {
  id: number;
  message: string;
  type: "success" | "error";
}) => void;
