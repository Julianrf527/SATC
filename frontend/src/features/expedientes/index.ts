// API pública de la feature expedientes: lista lateral de expedientes
// (filtros rápidos + búsqueda avanzada en BD) y piezas comunes del formulario
// de alta. Lo propio de cada módulo entra por adapter, config y slots.
export { default as ExpedienteList, type ExpedienteListProps } from "./ExpedienteList";
export { default as ExpedientesWorkspace } from "./ExpedientesWorkspace";
export { default as ExpedienteNoDisponibleModal } from "./ExpedienteNoDisponibleModal";
export { useExpedienteDesdeNavegacion } from "./useExpedienteDesdeNavegacion";
export { filtroArchivado, filtroMunicipio, filtroPorCampo } from "./filtrosRapidos";
export type {
  CampoTextoAvanzado,
  ExpedienteBase,
  ExpedienteListSlots,
  ExpedientesAdapter,
  ExpedientesConfig,
  FiltroAvanzadoBase,
  FiltroRapido,
  FiltrosAvanzadosSlotContext,
  NuevoExpedienteSlotContext,
  SetToast,
} from "./types";

// Formulario de alta: solo piezas comunes; cada módulo compone el suyo.
export { default as NuevoExpedienteLayout } from "./nuevo-expediente/NuevoExpedienteLayout";
export { default as UbicacionFields } from "./nuevo-expediente/UbicacionFields";
export { default as CampoTexto } from "./nuevo-expediente/CampoTexto";
export { useUbicacion, type UbicacionState } from "./nuevo-expediente/useUbicacion";
export { RADICADO_PATTERN, RADICADO_TITLE } from "./nuevo-expediente/radicado";
