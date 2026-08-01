import GestionLogsLayout from "../../Common/Layout/GestionLogsLayout";
import { API_CONFIG } from "../../../utils/api";

type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function InfraccionLogLayout({ setToast }: Props) {
  return (
    <GestionLogsLayout
      setToast={setToast}
      endpoint={API_CONFIG.ENDPOINTS.INFRACTION_AUDIT_LOGS}
      title="Auditoría de Infracciones"
      body="Registros de auditoría del módulo de infracciones"
      moduleName="Módulo Infracciones"
    />
  );
}
