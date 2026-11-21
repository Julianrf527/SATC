import { useCallback, type ReactNode } from "react";
import { BASE_URL } from "@shared/lib/api";
import { RECURSO_ENDPOINTS } from "@shared/lib/api/endpoints/recurso";
import { DocumentosProvider } from "@shared/lib/DocumentosProvider";

/**
 * Los documentos de lo que envuelve se abren por recurso
 * (/recurso/expedientes/{id}/archivos/{file_id}), que comprueba que sean del
 * expediente; app-docs ya no se consulta directo desde el navegador.
 */
export default function DocumentosExpediente({ expedienteId, children }: { expedienteId: number; children: ReactNode }) {
  const url = useCallback(
    (fileId: number) => `${BASE_URL}${RECURSO_ENDPOINTS.RECURSO_EXPEDIENTE_ARCHIVO(expedienteId, fileId)}`,
    [expedienteId],
  );
  return <DocumentosProvider url={url}>{children}</DocumentosProvider>;
}
