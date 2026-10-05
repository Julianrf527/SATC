import type { ReactNode } from "react";
import type { ModeloGenerico } from "@shared/types/common";
import type { Toast } from "@shared/lib/toastService";

/** Notificador de toasts que reciben los layouts de cada módulo. */
export type SetToast = (toast: Toast) => void;

/**
 * Campos mínimos que la lista necesita de un expediente. Cada módulo usa su
 * propio tipo (`Expediente` de infracción / sancionatorio) que extiende éste.
 * `municipio` e `involucrados` pueden faltar en respuestas del filtro avanzado.
 */
export type ExpedienteBase = {
  id: number;
  radicado: string;
  fecha_creacion: string;
  municipio?: ModeloGenerico | null;
  involucrados?: { nombre: string; numero_documento: number | string }[];
  archivado?: boolean;
};

/** Filtros del modal avanzado comunes a ambos servicios. */
export type FiltroAvanzadoBase = {
  direccion?: string;
  municipio_id?: number;
  vereda_ids?: number[];
  recurso_ids?: number[];
  valor_exacto: boolean;
};

/**
 * Acceso a datos que inyecta cada módulo (endpoints de su servicio). La
 * feature nunca conoce rutas concretas.
 */
export type ExpedientesAdapter<T extends ExpedienteBase, F extends FiltroAvanzadoBase> = {
  /** Clave raíz de react-query, p. ej. `["app-infraccion", "expedientes"]`. */
  queryKey: readonly unknown[];
  /** Búsqueda en BD con los filtros avanzados (ya limpios de vacíos). */
  filtrarAvanzado: (filtros: F) => Promise<T[]>;
  /** Veredas de un municipio para el filtro avanzado. */
  obtenerVeredas: (municipioId: number) => Promise<ModeloGenerico[]>;
};

/** Opción de un select. */
export type OpcionFiltro = { value: string; label: string };

/**
 * Filtro rápido (select local sobre la lista cargada).
 * - `derivado`: las opciones salen de los valores presentes en la lista.
 * - `fijo`: opciones fijas con predicado propio.
 */
export type FiltroRapido<T> = { id: string; etiquetaTodos: string } & (
  | { tipo: "derivado"; valor: (e: T) => string | null | undefined; ordenar?: boolean }
  | { tipo: "fijo"; opciones: OpcionFiltro[]; coincide: (e: T, valor: string) => boolean }
);

/** Campo de texto libre del modal avanzado (sección "Información del expediente"). */
export type CampoTextoAvanzado<F> = {
  clave: Extract<keyof F, string>;
  etiqueta: string;
  placeholder: string;
};

/** Configuración de presentación que define cada módulo. */
export type ExpedientesConfig<T extends ExpedienteBase, F extends FiltroAvanzadoBase> = {
  /** Segundo dato de la tarjeta (bajo el radicado), p. ej. "Fecha Radicado". */
  campoDestacado: { etiqueta: string; valor: (e: T) => string };
  /** Selects de filtros rápidos, en el orden en que se pintan. */
  filtrosRapidos: FiltroRapido<T>[];
  /** Campos de texto del modal avanzado, en orden. */
  camposTextoAvanzado: CampoTextoAvanzado<F>[];
};

/** Contexto que recibe el slot del formulario de nuevo expediente. */
export type NuevoExpedienteSlotContext = {
  /** Cierra el formulario y vuelve a la lista. */
  cerrar: () => void;
};

/** Contexto del slot de secciones extra del modal avanzado. */
export type FiltrosAvanzadosSlotContext<F> = {
  filtros: F;
  setFiltros: (updater: (prev: F) => F) => void;
};

export type ExpedienteListSlots<F> = {
  /**
   * Formulario de alta. Si se omite, la lista es de solo consulta (sin botón
   * "Nuevo Expediente").
   */
  renderNuevoExpediente?: (ctx: NuevoExpedienteSlotContext) => ReactNode;
  /** Secciones propias del módulo al final del modal de filtros avanzados. */
  renderFiltrosAvanzadosExtra?: (ctx: FiltrosAvanzadosSlotContext<F>) => ReactNode;
};
