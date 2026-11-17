import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@shared/context/AuthContext";
import { pestanaDeDocumento } from "../../manage/etapasProceso";
import type { NavegacionExpediente } from "../../types";

type Destino = {
  expediente_id: number;
  etapa_tipo?: string | null;
  tipo_documento?: string | null;
  /** Etapa del plan (pestaña) del documento (C.12). */
  etapa_padre?: string | null;
};

/**
 * Abre el expediente (y la pestaña de la etapa del documento) en Gestionar
 * o, si el usuario solo consulta, en Consulta. `null` si no tiene ninguna de
 * las dos pestañas (p. ej. un revisor sin permiso de lectura).
 */
export function useIrAlExpediente() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const permisos = new Set((user?.permisos ?? []).map((p) => p?.name));
  const ruta = permisos.has("recurso_gestionar") || permisos.has("recurso_super_gestion")
    ? "/recurso/manage"
    : permisos.has("recurso_consultar")
      ? "/recurso/consult"
      : null;

  const ir = useCallback(
    (d: Destino) => {
      if (!ruta) return;
      const state: NavegacionExpediente & { timestamp: number } = {
        expedienteIdToSelect: d.expediente_id,
        pestanaToSelect: pestanaDeDocumento(d.etapa_tipo, d.tipo_documento, d.etapa_padre),
        timestamp: Date.now(),
      };
      navigate(ruta, { state });
    },
    [navigate, ruta],
  );

  return { puedeIr: ruta !== null, puedeGestionar: ruta === "/recurso/manage", ir };
}
