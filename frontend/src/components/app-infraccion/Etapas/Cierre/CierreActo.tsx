import { useCallback, useEffect, useState } from "react";
import { apiCall, API_CONFIG } from "../../../../utils/api";
import ActoAdmin from "../../../Common/ActoAdministrativo/ActoAdmin";
import type { TipoNotificacion } from "../../../../types/sancionatorioApp";
import type { Involucrado } from "../../../../types/involucradoApp";

type Props = {
  etapaCierreId: number;
  expedienteId: number;
  actoAdmin: any | null; // formato ActoAdmin (sancionatoria-compatible, viene del backend)
  isEditable: boolean;
  setToast: (t: { id: number; message: string; type: "success" | "error" }) => void;
  onDataUpdated: () => void;
};

const INFRACTION_ENDPOINTS = {
  actoAdmin: {
    create: API_CONFIG.ENDPOINTS.INFRACTION_ACTO_ADMIN,
    update: API_CONFIG.ENDPOINTS.INFRACTION_ACTO_ADMIN_UPDATE,
    delete: API_CONFIG.ENDPOINTS.INFRACTION_ACTO_ADMIN_DELETE,
  },
  notificacion: {
    base: API_CONFIG.ENDPOINTS.INFRACTION_NOTIFICACION,
    delete: API_CONFIG.ENDPOINTS.INFRACTION_NOTIFICACION_DELETE,
  },
};

export default function CierreActo({
  etapaCierreId,
  expedienteId,
  actoAdmin,
  isEditable,
  setToast,
  onDataUpdated,
}: Props) {
  const [involucrados, setInvolucrados] = useState<Involucrado[]>([]);
  const [tiposNotificacion, setTiposNotificacion] = useState<TipoNotificacion[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const [invRes, tiposRes] = await Promise.all([
          apiCall(API_CONFIG.ENDPOINTS.INFRACTION_INVOLVED_LIST(expedienteId), { method: "GET" }),
          apiCall(API_CONFIG.ENDPOINTS.INFRACTION_TIPO_NOTIFICACION, { method: "GET" }),
        ]);
        if (invRes.ok) setInvolucrados(invRes.data?.involucrados ?? []);
        if (tiposRes.ok) setTiposNotificacion(tiposRes.data ?? []);
      } catch { /* silently ignore */ }
    })();
  }, [expedienteId]);

  const handleActoAdminUpdate = useCallback(() => {
    onDataUpdated();
  }, [onDataUpdated]);

  return (
    <ActoAdmin
      expedienteId={expedienteId}
      actoAdmin={actoAdmin ?? {}}
      etapaId={0}
      tipoEtapa="infraccion_cierre"
      tipoActo="notificacion"
      setToast={setToast}
      isEditable={isEditable}
      involucrados={involucrados}
      tiposNotificacion={tiposNotificacion}
      onActoAdminUpdate={handleActoAdminUpdate}
      endpoints={INFRACTION_ENDPOINTS}
      stageBinding={{ type: "etapa_cierre", id: etapaCierreId }}
      embedded
    />
  );
}
