import GestionLogsLayout from "../../Common/Layout/GestionLogsLayout";
import { API_CONFIG } from "../../../utils/api";

type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function ExpedienteLogLayout({ setToast }: Props) {
  return (
    <GestionLogsLayout
      setToast={setToast}
      endpoint={API_CONFIG.ENDPOINTS.FILE_AUDIT_LOGS}
      title="Auditoría de Expedientes"
      body="Registros de auditoría del módulo sancionatorio"
      moduleName="Módulo Sancionatorio"
    />
  );
}
