import { AlertasExpediente } from "@features/alertas";
import { API_CONFIG } from "@shared/lib/api";

type Props = {
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
};

export default function AlertasInfraccionLayout({ setToast }: Props) {
  return (
    <AlertasExpediente
      alertsAllEndpoint={API_CONFIG.ENDPOINTS.INFRACTION_ALERTS_ALL}
      rutas={{ gestion: "/infraction/manage", consulta: "/infraction/consult" }}
      processName="Módulo de Infracciones"
      setToast={setToast}
    />
  );
}
