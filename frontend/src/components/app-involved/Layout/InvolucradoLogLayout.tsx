import GestionLogsLayout from "../../Common/Layout/GestionLogsLayout";
import { API_CONFIG } from "../../../utils/api";

type Props = {
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
};

export default function InvolucradoLogLayout({ setToast }: Props) {
  return (
    <GestionLogsLayout
      setToast={setToast}
      endpoint={API_CONFIG.ENDPOINTS.INVOLVED_LOG}
      title="Auditoría de Involucrados"
      body="Registros de auditoría del módulo de involucrados"
      moduleName="Módulo Involucrados"
    />
  );
}
