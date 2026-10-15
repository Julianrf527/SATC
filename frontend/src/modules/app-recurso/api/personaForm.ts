/** Formulario de una persona de app-involved (todo como texto). */
export type PersonaForm = {
  tipo_documento: string;
  numero_documento: string;
  digito_verificacion: string;
  nombre: string;
  celular: string;
  correo: string;
  direccion: string;
};

export const PERSONA_VACIA: PersonaForm = {
  tipo_documento: "CC",
  numero_documento: "",
  digito_verificacion: "",
  nombre: "",
  celular: "",
  correo: "",
  direccion: "",
};
