import type { CodigoEtapa } from "../../manage/etapasProceso";
import type { Actuacion, EtapaActoTipo } from "../../types";

export type FiltrosMisActuaciones = {
  radicado: string;
  /** `tipo_documento` (INFORME_VISITA, ACTO_CIERRE...) o "all". */
  tipo: string;
  /** `categoria:rol` (p. ej. "acto:revisor") o "all". */
  rol: string;
  estado: string;
  soloMiTurno: boolean;
};

export const FILTROS_MIS_ACTUACIONES: FiltrosMisActuaciones = {
  radicado: "",
  tipo: "all",
  rol: "all",
  estado: "all",
  soloMiTurno: false,
};

/**
 * Clave del filtro "Estado". Un informe aceptado (por flujo o cargue manual)
 * es "Aceptado"; lo demás usa el estado del proceso que manda el backend.
 */
export const claveEstado = (a: Actuacion): string =>
  a.informe?.aceptado ? "__aceptado" : (a.estado_proceso?.codigo ?? "__sin_proceso");

const etiquetaEstado = (a: Actuacion): string =>
  a.informe?.aceptado ? "Aceptado" : (a.estado_proceso?.etiqueta ?? "Sin proceso");

/** Opciones del filtro "Estado" con los estados presentes en la lista. */
export function opcionesEstado(actuaciones: Actuacion[]): { value: string; label: string }[] {
  const vistos = new Map<string, string>();
  for (const a of actuaciones) vistos.set(claveEstado(a), etiquetaEstado(a));
  return [...vistos].map(([value, label]) => ({ value, label })).sort((a, b) => a.label.localeCompare(b.label));
}

/** Filtro en cliente (/mis-actuaciones devuelve todo lo del usuario). */
export function filtrarActuaciones(actuaciones: Actuacion[], f: FiltrosMisActuaciones): Actuacion[] {
  const radicado = f.radicado.trim().toLowerCase();
  return actuaciones.filter(
    (a) =>
      (!radicado || (a.expediente_radicado ?? "").toLowerCase().includes(radicado)) &&
      (f.tipo === "all" || a.tipo_documento === f.tipo) &&
      (f.rol === "all" || a.roles.some((r) => `${a.categoria}:${r.codigo}` === f.rol)) &&
      (f.estado === "all" || claveEstado(a) === f.estado) &&
      (!f.soloMiTurno || a.requiere_mi_accion),
  );
}

/** Pestaña del expediente (DetalleInfraccion) donde vive el documento. */
const ETAPA_DEL_ACTO: Record<EtapaActoTipo, CodigoEtapa> = {
  medida_preventiva: "respuesta",
  etapa_concepto: "concepto",
  etapa_cierre: "cierre",
};

export function pestanaDeActuacion(a: Actuacion): CodigoEtapa {
  // El acto del acoger concepto · seguimiento comparte etapa_tipo con el de la visita.
  if (a.tipo_documento === "ACTO_CONCEPTO_SEGUIMIENTO") return "concepto_seguimiento";
  if (a.acto) return ETAPA_DEL_ACTO[a.acto.etapa_tipo];
  return (a.informe?.tipo_informe ?? "").toUpperCase() === "SEGUIMIENTO" ? "seguimiento" : "visita";
}
