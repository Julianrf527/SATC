import type { ReactNode } from "react";
import { DocumentosContext, type UrlDocumento } from "./documentos";

/** Cambia de dónde se abren los documentos para todo lo que envuelve. */
export function DocumentosProvider({ url, children }: { url: UrlDocumento; children: ReactNode }) {
  return <DocumentosContext.Provider value={url}>{children}</DocumentosContext.Provider>;
}
