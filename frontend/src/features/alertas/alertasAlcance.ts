// Lógica pura del filtro "Mis expedientes / Todos" de la pestaña Alertas y del
// destino del enlace de cada alerta. Las rutas las inyecta el módulo (sin
// banderas por módulo aquí).

/** `mios`: expedientes a cargo del usuario (por defecto). `todos`: todos. */
export type AlcanceAlertas = "mios" | "todos";

/** Textos del selector de alcance (el módulo puede cambiarlos). */
export type EtiquetasAlcance = { titulo: string; mios: string; todos: string };

export const ETIQUETAS_ALCANCE: EtiquetasAlcance = { titulo: "Expedientes", mios: "Mis expedientes", todos: "Todos" };

export function opcionesAlcance(
  etiquetas: Partial<EtiquetasAlcance> = {},
): { value: AlcanceAlertas; label: string }[] {
  const e = { ...ETIQUETAS_ALCANCE, ...etiquetas };
  return [
    { value: "mios", label: e.mios },
    { value: "todos", label: e.todos },
  ];
}

/**
 * "Pendiente: Líder técnico, SIG" si la alerta es de uno o varios roles
 * (`roles_responsables`); null si es del encargado.
 */
export function textoRolesResponsables(alerta: { roles_responsables?: { etiqueta: string }[] | null }): string | null {
  const roles = alerta.roles_responsables ?? [];
  return roles.length ? `Pendiente: ${roles.map((r) => r.etiqueta).join(", ")}` : null;
}

/** Pantallas a las que lleva el enlace de una alerta (las define el módulo). */
export type RutasAlertas = {
  /** Expediente a cargo del usuario: pantalla de gestión. */
  gestion: string;
  /** Expediente de otro responsable: pantalla de consulta (solo lectura). */
  consulta: string;
};

/**
 * A dónde lleva el botón de una alerta. `accion` es el texto del botón. Un
 * módulo puede dar su propio destino (prop `destino` de AlertasExpediente);
 * lo que no indique se completa como siempre (ver `resolverDestino`).
 */
export type DestinoAlerta = {
  ruta: string;
  accion: string;
  /** Botón resaltado (verde). Por defecto, solo si `accion` es "Gestionar". */
  principal?: boolean;
  /** Tooltip del botón. */
  title?: string;
  /** `location.state` al navegar. Por defecto, el `estadoNavegacion` del módulo. */
  estado?: Record<string, unknown>;
};

export type DestinoResuelto = Required<DestinoAlerta>;

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

/**
 * Destino completo del botón de una alerta. Sin `personalizado` (o si
 * devuelve null) es el de siempre: `destinoAlerta` con las rutas del módulo,
 * resaltado si es Gestionar y con el `estadoNavegacion` del módulo.
 */
export function resolverDestino<A extends { es_responsable?: boolean }>(
  alerta: A,
  rutas: RutasAlertas,
  estadoNavegacion: (alerta: A) => Record<string, unknown>,
  personalizado?: (alerta: A) => DestinoAlerta | null,
): DestinoResuelto {
  const d = personalizado?.(alerta) ?? destinoAlerta(alerta, rutas);
  const principal = d.principal ?? d.accion === "Gestionar";
  return {
    ruta: d.ruta,
    accion: d.accion,
    principal,
    title: d.title ?? (principal ? "Expediente a su cargo" : "Expediente de otro responsable (solo lectura)"),
    estado: d.estado ?? estadoNavegacion(alerta),
  };
}
