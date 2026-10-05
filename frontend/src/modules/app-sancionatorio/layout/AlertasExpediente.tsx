import { AlertasExpediente } from "@features/alertas";
import { API_CONFIG } from "@shared/lib/api";

type Props = {
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
};

export default function AlertsLayout({ setToast }: Props) {
  return (
    <AlertasExpediente
      alertsAllEndpoint={API_CONFIG.ENDPOINTS.FILE_ALERTS_ALL}
      navigatePath="/file/manage"
      processName="Módulo Sancionatorio"
      setToast={setToast}
    />
  );
}
