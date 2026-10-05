import { GestionLogsLayout, type AuditLogConfig } from "@features/auditoria";
import { INFRACTION_ENDPOINTS } from "@shared/lib/api";

type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

/** Config explícita de auditoría de app-infraction (antes se deducía del endpoint). */
const INFRACCION_AUDIT_CONFIG: AuditLogConfig = {
  documentoParam: "cedula",
  showRadicado: true,
  mappingSources: {
    municipios: INFRACTION_ENDPOINTS.INFRACTION_TOWNS_RURAL_DISTRICT,
    recursos: INFRACTION_ENDPOINTS.INFRACTION_AFFECTED_RESOURCE,
    causas: INFRACTION_ENDPOINTS.INFRACTION_TIPOS_AFECTACION,
    quejosos: INFRACTION_ENDPOINTS.INFRACTION_COMPLAINER,
  },
};

export default function InfraccionLogLayout({ setToast }: Props) {
  return (
    <GestionLogsLayout
      setToast={setToast}
      endpoint={INFRACTION_ENDPOINTS.INFRACTION_AUDIT_LOGS}
      title="Auditoría de Infracciones"
      moduleName="Módulo Infracciones"
      config={INFRACCION_AUDIT_CONFIG}
    />
  );
}
