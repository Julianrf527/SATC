import { GestionEncargadoLayout as GestionarEncargadoLayout } from "@features/gestion-encargado";
import { API_CONFIG } from "@shared/lib/api";
type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function EncargadoExpedienteLayout({ setToast }: Props) {
  return (
    <GestionarEncargadoLayout
      endpoints={{
        lista: API_CONFIG.ENDPOINTS.FILES,
        bulkUpdate: API_CONFIG.ENDPOINTS.FILE_BULK_UPDATE_ENCARGADO,
      }}
      title="Asignar Encargados"
      modulo="Módulo Sancionatorio"
      setToast={setToast}
    />
  );
}
