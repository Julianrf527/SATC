import { createContext, useContext, useMemo } from "react";
import { getDocumentUrl } from "./documentViewer";

/** URL desde la que el navegador abre un documento por su file_id. */
export type UrlDocumento = (fileId: number) => string;

/**
 * Por defecto, la ruta de app-docs. Un módulo que sirve sus propios archivos
 * (p. ej. recurso: /recurso/expedientes/{id}/archivos/{file_id}) la cambia con
 * `DocumentosProvider` para todo lo que quede dentro.
 */
export const DocumentosContext = createContext<UrlDocumento>(getDocumentUrl);

/** `url(fileId)` y `abrir(fileId)` (pestaña nueva) según el módulo que envuelve. */
export function useDocumentos() {
  const url = useContext(DocumentosContext);
  return useMemo(() => ({ url, abrir: (fileId: number) => void window.open(url(fileId), "_blank") }), [url]);
}
