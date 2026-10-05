import { ActoAdmin } from "@features/acto-administrativo";
import type { ActoAdministrativo } from "@shared/types/sancionatorio";
import { useDatosActoAdmin } from "../../api/expediente";
import { INFRACCION_ACTO_ENDPOINTS_SOLO_NOTIFICACION } from "../actoAdminEndpoints";

type Props = {
  etapaCierreId: number;
  expedienteId: number;
  actoAdmin: ActoAdministrativo | null; // formato ActoAdmin (sancionatoria-compatible, viene del backend)
  isEditable: boolean;
  setToast: (t: { id: number; message: string; type: "success" | "error" }) => void;
  onDataUpdated: () => void;
};

export default function CierreActo({
  etapaCierreId,
  expedienteId,
  actoAdmin,
  isEditable,
  setToast,
  onDataUpdated,
}: Props) {
  const { involucrados, tiposNotificacion } = useDatosActoAdmin(expedienteId);

  return (
    <ActoAdmin
      expedienteId={expedienteId}
      actoAdmin={actoAdmin ?? {}}
      etapaId={0}
      tipoActo="notificacion"
      setToast={setToast}
      isEditable={isEditable}
      involucrados={involucrados}
      tiposNotificacion={tiposNotificacion}
      onActoAdminUpdate={onDataUpdated}
      endpoints={INFRACCION_ACTO_ENDPOINTS_SOLO_NOTIFICACION}
      stageBinding={{ type: "etapa_cierre", id: etapaCierreId }}
      embedded
    />
  );
}
