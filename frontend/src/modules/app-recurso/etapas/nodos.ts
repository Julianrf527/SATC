// Identidad de cada nodo del árbol de etapas y las rutas de sus acciones
// (API.md C.3–C.10). Lógica pura: se prueba en nodos.test.ts.
//
// Se importa el archivo de endpoints directo (no `@shared/lib/api`) para que
// los tests corran en node: el cliente HTTP usa `window`.
import { RECURSO_ENDPOINTS } from "@shared/lib/api/endpoints/recurso";
import type { AccionEtapa, AmbitoRequerimiento, NodoEtapa, TipoConcepto } from "../types";

/** Qué nodo del árbol es (para armar sus rutas). */
export type RefNodo =
  | { clase: "admite" }
  | { clase: "concepto"; tipo: TipoConcepto }
  | { clase: "requerimiento"; ambito: AmbitoRequerimiento }
  | { clase: "decision" }
  | { clase: "recurso" }
  | { clase: "memorias" }
  | { clase: "subsanacion" }
  | { clase: "aprobacion_memorias" }
  | { clase: "obras" }
  | { clase: "informe" }
  | { clase: "nuevo_informe" }
  | { clase: "aprobacion_obras" }
  | { clase: "tercero"; vinculoId: number };

/** Ruta base (relativa a `/etapas/{exp}`) de los nodos con encargado o técnico. */
function rutaBase(ref: RefNodo): string | null {
  switch (ref.clase) {
    case "admite":
      return "admite";
    case "concepto":
      return `conceptos/${ref.tipo}`;
    case "requerimiento":
      return `requerimientos/${ref.ambito}`;
    case "decision":
      return "decision";
    case "recurso":
      return "recurso";
    case "aprobacion_memorias":
      return "memorias/aprobacion";
    case "aprobacion_obras":
      return "obras/aprobacion";
    default:
      return null;
  }
}

/** POST "Asignarme para diligenciar" (C.3, C.5–C.8, C.10). */
export function urlAsignarme(expedienteId: number, ref: RefNodo): string | null {
  if (ref.clase === "tercero") return RECURSO_ENDPOINTS.RECURSO_TERCERO_ASIGNARME(ref.vinculoId);
  const base = rutaBase(ref);
  return base && ref.clase !== "concepto" ? RECURSO_ENDPOINTS.RECURSO_ETAPA_ACCION(expedienteId, `${base}/asignarme`) : null;
}

/** POST "Cargar versión final" (acto firmado o concepto firmado). */
export function urlVersionFinal(expedienteId: number, ref: RefNodo): string | null {
  if (ref.clase === "tercero") return RECURSO_ENDPOINTS.RECURSO_TERCERO_VERSION_FINAL(ref.vinculoId);
  const base = rutaBase(ref);
  return base ? RECURSO_ENDPOINTS.RECURSO_ETAPA_ACCION(expedienteId, `${base}/version-final`) : null;
}

/** POST seleccionar técnico de un concepto (no aplica a `etapa2`, C.4). */
export function urlSeleccionarTecnico(expedienteId: number, tipo: TipoConcepto): string | null {
  return tipo === "etapa2" ? null : RECURSO_ENDPOINTS.RECURSO_ETAPA_ACCION(expedienteId, `conceptos/${tipo}/tecnico`);
}

/** POST que registra un documento radicado por el usuario (`Radicado` → 201). */
export function urlRegistrarRadicado(expedienteId: number, ref: RefNodo): string | null {
  const rutas: Partial<Record<RefNodo["clase"], string>> = {
    recurso: "recurso",
    memorias: "memorias",
    subsanacion: "memorias/subsanacion",
    obras: "obras",
    nuevo_informe: "obras/nuevo-informe",
  };
  const ruta = rutas[ref.clase];
  return ruta ? RECURSO_ENDPOINTS.RECURSO_ETAPA_ACCION(expedienteId, ruta) : null;
}

/**
 * POST de cargue directo (super gestión, C.9). La aprobación de memorias /
 * obras y el informe viven en la fila de su etapa, así que usan su ruta.
 */
export function urlSuperCargue(expedienteId: number, ref: RefNodo): string {
  const r = (ruta: string) => RECURSO_ENDPOINTS.RECURSO_SUPER_GESTION(expedienteId, ruta);
  switch (ref.clase) {
    case "tercero":
      return RECURSO_ENDPOINTS.RECURSO_SUPER_GESTION_TERCERO_ACTO(ref.vinculoId);
    case "concepto":
      return r(`conceptos/${ref.tipo}`);
    case "requerimiento":
      return r(`requerimientos/${ref.ambito}`);
    case "aprobacion_memorias":
    case "memorias":
      return r("memorias");
    case "subsanacion":
      return r("memorias/subsanacion");
    case "aprobacion_obras":
    case "obras":
    case "informe":
      return r("obras");
    case "nuevo_informe":
      return r("obras/nuevo-informe");
    default:
      return r(ref.clase);
  }
}

/** Acciones del nodo que el usuario puede usar aquí (en Consulta no hay ninguna). */
export function accionesNodo(nodo: Pick<NodoEtapa, "acciones_disponibles"> | null | undefined, isEditable: boolean) {
  const lista = isEditable ? (nodo?.acciones_disponibles ?? []) : [];
  return (codigo: AccionEtapa) => lista.includes(codigo);
}
