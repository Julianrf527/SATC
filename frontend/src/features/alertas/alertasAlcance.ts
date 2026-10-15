// Lógica pura del filtro "Mis expedientes / Todos" de la pestaña Alertas y del
// destino del enlace de cada alerta. Las rutas las inyecta el módulo (sin
// banderas por módulo aquí).

/** `mios`: expedientes a cargo del usuario (por defecto). `todos`: todos. */
export type AlcanceAlertas = "mios" | "todos";

export const ALCANCE_OPCIONES: { value: AlcanceAlertas; label: string }[] = [
  { value: "mios", label: "Mis expedientes" },
  { value: "todos", label: "Todos" },
];

/** Pantallas a las que lleva el enlace de una alerta (las define el módulo). */
export type RutasAlertas = {
  /** Expediente a cargo del usuario: pantalla de gestión. */
  gestion: string;
  /** Expediente de otro responsable: pantalla de consulta (solo lectura). */
  consulta: string;
};

export type DestinoAlerta = { ruta: string; accion: "Gestionar" | "Consultar" };

/**
 * Endpoint de "todas las alertas" según el alcance. Con `mios` se deja tal
 * cual (el backend asume `mios` por defecto), así el endpoint coincide con el
 * de antes del filtro.
 */
export function endpointConAlcance(endpoint: string, alcance: AlcanceAlertas): string {
  if (alcance === "mios") return endpoint;
  const sep = endpoint.includes("?") ? "&" : "?";
  return `${endpoint}${sep}alcance=${alcance}`;
}

/**
 * Destino del enlace de una alerta: Gestionar si el usuario es el responsable
 * del expediente; Consultar si no. Sin `es_responsable` (backend anterior al
 * filtro, que solo devolvía los propios) se asume responsable.
 */
export function destinoAlerta(
  alerta: { es_responsable?: boolean },
  rutas: RutasAlertas,
): DestinoAlerta {
  return alerta.es_responsable === false
    ? { ruta: rutas.consulta, accion: "Consultar" }
    : { ruta: rutas.gestion, accion: "Gestionar" };
}
