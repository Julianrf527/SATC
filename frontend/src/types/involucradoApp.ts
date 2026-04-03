export interface Involucrado {
  id: number;
  numero_documento: number;
  digito_verificacion?: string | null;
  tipo_documento: string;
  nombre: string;
  celular: number;
  correo: string;
}