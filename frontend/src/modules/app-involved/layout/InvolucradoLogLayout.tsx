import { GestionLogsLayout } from "@features/auditoria";
import { API_CONFIG } from "@shared/lib/api";
import type { SetToast } from "../types";

type Props = {
  setToast: SetToast;
};

export default function InvolucradoLogLayout({ setToast }: Props) {
  return (
    <GestionLogsLayout
      setToast={setToast}
      endpoint={API_CONFIG.ENDPOINTS.INVOLVED_LOG}
      title="Auditoría de Involucrados"
      moduleName="Módulo Involucrados"
      config={{ documentoParam: "documento_usuario", showRadicado: false, mappingSources: {} }}
    />
  );
}
