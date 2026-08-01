import AlertasExpediente from "../../Common/Layout/AlertasExpediente";
import { API_CONFIG } from "../../../utils/api";

type Props = {
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
};

export default function AlertasInfraccionLayout({ setToast }: Props) {
  return (
    <AlertasExpediente
      alertsAllEndpoint={API_CONFIG.ENDPOINTS.INFRACTION_ALERTS_ALL}
      navigatePath="/infraction/manage"
      processName="Módulo de Infracciones"
      setToast={setToast}
    />
  );
}
