import { GestionEncargadoLayout as GestionarEncargadoLayout } from "@features/gestion-encargado";
import { API_CONFIG } from "@shared/lib/api";
type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function EncargadoInfraccionLayout({ setToast }: Props) {
  return (
    <GestionarEncargadoLayout
      endpoints={{
        lista: API_CONFIG.ENDPOINTS.INFRACTIONS,
        bulkUpdate: API_CONFIG.ENDPOINTS.INFRACTION_BULK_UPDATE_ENCARGADO,
      }}
      title="Asignar Encargados"
      modulo="Módulo de Infracciones"
      showExpediente={false}
      setToast={setToast}
    />
  );
}
