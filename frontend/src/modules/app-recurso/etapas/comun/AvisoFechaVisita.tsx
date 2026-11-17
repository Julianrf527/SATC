import { useQuery } from "@tanstack/react-query";
import { AlertTriangle } from "lucide-react";
import { apiRequest, RECURSO_ENDPOINTS } from "@shared/lib/api";
import { recursoKeys } from "../../api/queryKeys";
import { fechaValida } from "../formularios/comunes";

type AvisoVisita = { fecha_limite: string; dias_habiles: number; advertencia: string | null };

/**
 * Aviso amarillo (no bloquea) cuando la fecha de visita técnica es anterior
 * al numerado del auto que admite o cae después de los 10 días hábiles
 * siguientes. La regla (festivos incluidos) la resuelve el backend
 * (`GET /recurso/alertas/aviso-visita`); aquí solo se muestra.
 */
export default function AvisoFechaVisita({ fechaNumerado, fechaVisita }: { fechaNumerado: string; fechaVisita: string }) {
  const habilitado = fechaValida(fechaNumerado) && fechaValida(fechaVisita);
  const { data } = useQuery({
    queryKey: recursoKeys.avisoVisita(fechaNumerado, fechaVisita),
    queryFn: async () => {
      const qs = new URLSearchParams({ fecha_numerado: fechaNumerado, fecha_visita: fechaVisita });
      return (await apiRequest<{ data: AvisoVisita }>(`${RECURSO_ENDPOINTS.RECURSO_ALERTAS_AVISO_VISITA}?${qs}`)).data;
    },
    enabled: habilitado,
    staleTime: Infinity,
  });
  if (!habilitado || !data?.advertencia) return null;
  return (
    <div role="alert" className="alert alert-warning text-sm">
      <AlertTriangle size={18} />
      <span>{data.advertencia}</span>
    </div>
  );
}
