import type {
  DatosRevision,
  DatosVersion,
  ProcesoDetalle,
  ResultadoAccion,
  RevisionProceso,
  VersionProceso,
} from "./types";

/**
 * Lo que cada módulo inyecta para conectar la feature con SU backend. La
 * feature no conoce endpoints ni nombres de campos del formulario: el adapter
 * arma el FormData con los nombres que espera su servicio.
 *
 * `D` permite tipar los campos extra que un flujo agrega a `ProcesoDetalle`
 * (llegan intactos a los slots del modal).
 */
export interface ProcesoAdapter<D extends ProcesoDetalle = ProcesoDetalle> {
  /** Clave react-query del detalle (jerárquica, bajo la clave del módulo). */
  queryKey(id: number): readonly unknown[];
  detalle(id: number): Promise<D>;
  revisar(id: number, datos: DatosRevision): Promise<ResultadoAccion>;
  subirVersion(id: number, datos: DatosVersion): Promise<ResultadoAccion>;
  /**
   * Ruta (relativa a BASE_URL) para descargar el archivo de una versión.
   * Recibe también el id del proceso: hay backends que anidan la descarga
   * bajo el proceso (`/{id}/versiones/{version_id}/descarga`).
   */
  urlVersion(id: number, version: VersionProceso): string;
  /** Ruta (relativa a BASE_URL) del adjunto de una revisión. */
  urlAdjunto(id: number, revision: RevisionProceso): string;
}
