import type { CatalogosRecurso, EtapasExpediente, ExpedienteDetalle, SetToast } from "../types";

/** Props que reciben todas las pestañas del detalle (cada una usa lo que necesita). */
export type EtapaProps = {
  expediente: ExpedienteDetalle;
  /** Árbol de etapas: clave `etapas` de GET /expedientes/{id} (API.md C.2). */
  etapas: EtapasExpediente;
  catalogos: CatalogosRecurso;
  setToast: SetToast;
  /** `false` en Consulta (solo lectura). Las acciones salen de `acciones_disponibles`. */
  isEditable: boolean;
};

/** Lo que necesitan las tarjetas de nodo (sub-procesos) de cualquier etapa. */
export type EntornoEtapa = Pick<EtapaProps, "expediente" | "catalogos" | "setToast" | "isEditable">;
