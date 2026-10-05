// API pública de features/proceso-revision: motor genérico de revisión de
// documentos (versiones, revisiones, auditoría, acciones por usuario).
//
// No conoce flujos concretos (regla ESLint activa): cada módulo inyecta un
// `ProcesoAdapter` (endpoints + FormData) y lo propio entra por slots.
//
//   <ProcesoDetalleModal adapter={docsAdapter} id={docId} isOpen onClose={...}
//     onCambio={() => invalidarLista()} extraAcciones={(d) => <MiBoton />} />
export type { ProcesoAdapter } from "./adapter";
export type {
  AccionDisponible,
  ArchivoProceso,
  AuditoriaProceso,
  CambioProceso,
  DatosRevision,
  DatosVersion,
  EstadoProceso,
  ProcesoDetalle,
  ReglaAdjunto,
  ResultadoAccion,
  RevisionProceso,
  RevisorProceso,
  SubidaVersion,
  TonoProceso,
  VersionProceso,
} from "./types";
export {
  usePrecargarProceso,
  useProcesoRevision,
  type ProcesoRevisionState,
  type UseProcesoRevisionOpciones,
} from "./useProcesoRevision";
export {
  ProcesoDetalleModal,
  type ProcesoDetalleModalProps,
  type SlotProceso,
} from "./ProcesoDetalleModal";
export { ListaVersiones } from "./ListaVersiones";
export { HistorialRevisiones } from "./HistorialRevisiones";
export { TimelineAuditoria } from "./TimelineAuditoria";
export { FormRevision } from "./FormRevision";
export { FormSubirVersion } from "./FormSubirVersion";
