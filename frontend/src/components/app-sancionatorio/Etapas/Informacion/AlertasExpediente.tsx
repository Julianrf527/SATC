import Alertas from "../../../Common/Layout/Alertas";
import { API_CONFIG } from "../../../../utils/api";

interface Props {
  expedienteId: number;
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
}

export default function Alerts({ expedienteId, setToast }: Props) {
  return (
    <Alertas
      expedienteId={expedienteId}
      alertEndpoint={API_CONFIG.ENDPOINTS.FILE_ALERTS(expedienteId)}
      setToast={setToast}
    />
  );
}
