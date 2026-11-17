import { lazy, type ComponentType, type LazyExoticComponent } from "react";

export type EtapaTab = {
  id: string;
  label: string;
  /** Clase boxicons. */
  icon: string;
  /** tipo_etapa_id del backend (null = siempre disponible). */
  tipoEtapaId: number | null;
  // Cada etapa tiene props distintas; DetalleExpediente les pasa un set común.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  component: LazyExoticComponent<ComponentType<any>>;
};

/** Pestañas del detalle del expediente sancionatorio, en orden del proceso. */
export const ETAPAS_TABS: EtapaTab[] = [
  { id: "info", label: "Información", icon: "bx-info-circle", tipoEtapaId: null, component: lazy(() => import("../etapas/InformacionExpediente")) },
  { id: "indagacion", label: "Indagación Preliminar", icon: "bx-search-alt", tipoEtapaId: 2, component: lazy(() => import("../etapas/InvestigacionPreliminar")) },
  { id: "detalle", label: "Medida Preventiva", icon: "bx-error-alt", tipoEtapaId: 1, component: lazy(() => import("../etapas/DetalleMedidaPreventiva")) },
  { id: "inicio", label: "Inicio Proceso Sancionatorio", icon: "bx-book-bookmark", tipoEtapaId: 9, component: lazy(() => import("../etapas/InicioProcesoSancionatorio")) },
  { id: "cesacion", label: "Cesacion", icon: "bx-error-alt", tipoEtapaId: 10, component: lazy(() => import("../etapas/Cesacion")) },
  { id: "cargos", label: "Formulación de Cargos", icon: "bx-file", tipoEtapaId: 4, component: lazy(() => import("../etapas/FormulacionCargos")) },
  { id: "apertura_ep", label: "Apertura Etapa Probatoria", icon: "bx-cabinet", tipoEtapaId: 5, component: lazy(() => import("../etapas/AperturaEtapaProbatoria")) },
  { id: "cierre_ep", label: "Cierre Etapa Probatoria", icon: "bx-cabinet", tipoEtapaId: 11, component: lazy(() => import("../etapas/CierreEtapaProbatoria")) },
  { id: "decision", label: "Decisión de Fondo", icon: "bx-check-circle", tipoEtapaId: 6, component: lazy(() => import("../etapas/DecisionFondo")) },
  { id: "recurso", label: "Probatoria del Recurso", icon: "bx-calendar-check", tipoEtapaId: 12, component: lazy(() => import("../etapas/Recurso")) },
  { id: "ejecucion", label: "Ejecución Sanción", icon: "bx-calendar-check", tipoEtapaId: 7, component: lazy(() => import("../etapas/EjecucionSancion")) },
];
