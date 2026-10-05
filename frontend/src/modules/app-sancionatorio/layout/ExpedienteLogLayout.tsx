import { GestionLogsLayout, type AuditLogConfig } from "@features/auditoria";
import { API_CONFIG } from "@shared/lib/api";
import type { SetToast } from "../types";

type Props = {
  setToast: SetToast;
};

/** Config de auditoría del servicio sancionatorio (antes deducida del endpoint). */
const AUDIT_CONFIG: AuditLogConfig = {
  documentoParam: "cedula",
  showRadicado: true,
  mappingSources: {
    municipios: API_CONFIG.ENDPOINTS.TOWNS_SIDEWALK,
    recursos: API_CONFIG.ENDPOINTS.FILE_AFFECTED_RESOURCE,
  },
};

export default function ExpedienteLogLayout({ setToast }: Props) {
  return (
    <GestionLogsLayout
      setToast={setToast}
      endpoint={API_CONFIG.ENDPOINTS.FILE_AUDIT_LOGS}
      title="Auditoría de Expedientes"
      body="Registros de auditoría del módulo sancionatorio"
      moduleName="Módulo Sancionatorio"
      config={AUDIT_CONFIG}
    />
  );
}
