// Documentos del auto que admite (plan §4 etapa 1, C.3): campo del body ↔
// acción del backend que lo habilita. Lógica pura (documentosAdmite.test.ts).
import type { AccionEtapa, DatosAdmite } from "../../types";

export type CampoDocumentoAdmite = keyof DatosAdmite;

export const CAMPOS_DOCUMENTOS_ADMITE: { campo: CampoDocumentoAdmite; accion: AccionEtapa; etiqueta: string }[] = [
  { campo: "doc_oficio_alcaldia_id", accion: "cargar_oficio_alcaldia", etiqueta: "Oficio a la Alcaldía" },
  { campo: "doc_fijacion_aviso_id", accion: "cargar_fijacion_aviso", etiqueta: "Fijación del aviso en la corporación" },
  {
    campo: "doc_constancia_fijacion_aviso_id",
    accion: "cargar_constancia_fijacion",
    etiqueta: "Constancia de fijación de la Alcaldía",
  },
];

/** Campos que el usuario puede cargar según `acciones_disponibles`. */
export function documentosPermitidos(puede: (a: AccionEtapa) => boolean): CampoDocumentoAdmite[] {
  return CAMPOS_DOCUMENTOS_ADMITE.filter((c) => puede(c.accion)).map((c) => c.campo);
}
