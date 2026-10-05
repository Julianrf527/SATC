/** Involucrado tal como lo devuelve app-involved (/involved/manage). */
export type Involved = {
  id: number;
  numero_documento: number;
  digito_verificacion: string | null;
  tipo_documento: string;
  nombre: string;
  celular: number | null;
  correo: string | null;
  direccion?: string | null;
};

/** Payload de edición (documento solo si cambió). */
export type InvolvedSaveData = {
  nombre: string;
  numero_documento?: number;
  tipo_documento?: string;
  celular: number | null;
  correo: string | null;
  digito_verificacion: string | null;
  direccion: string | null;
};

export type InvolvedFiltros = {
  page: number;
  limit: number;
  numeroDocumento: string;
  tipoDocumento: string;
  nombre: string;
  correo: string;
};

export type InvolvedListResponse = {
  data?: Involved[];
  totalCount?: number;
};

export type SetToast = (toast: {
  id: number;
  message: string;
  type: "success" | "error";
}) => void;
