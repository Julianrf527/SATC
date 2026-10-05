import { Alertas } from "@features/alertas";
import { API_CONFIG } from "@shared/lib/api";

interface Props {
  expediente_id: number;
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
}

export default function AlertasInfraccion({ expediente_id, setToast }: Props) {
  return (
    <Alertas
      expedienteId={expediente_id}
      alertEndpoint={API_CONFIG.ENDPOINTS.INFRACTION_ALERTS(expediente_id)}
      setToast={setToast}
    />
  );
}
