import type { Involucrado } from "@shared/types/involucrado";

/** Endpoints que inyecta cada módulo (infracción / sancionatorio). */
export type InvolucradosExpedienteEndpoints = {
  vincular: string;
  desvincular: (id: number) => string;
  /** Listado de involucrados del expediente. */
  listar: (expedienteId: number) => string;
};

export type SetToast = (toast: {
  id: number;
  message: string;
  type: "success" | "error";
}) => void;

/** Estado del formulario de alta/vinculación (todo como texto). */
export type InvolucradoForm = {
  numero_documento: string;
  digito_verificacion: string;
  tipo_documento: string;
  nombre: string;
  celular: string;
  correo: string;
  direccion: string;
};

export type VincularInvolucradoInput = {
  formData: InvolucradoForm;
  existingInvolucrado: Involucrado | null;
  /** Lista actual, para no duplicar vínculos. */
  actuales: Involucrado[];
};
