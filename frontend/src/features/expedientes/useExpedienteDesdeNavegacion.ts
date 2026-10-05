import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import type { ExpedienteBase } from "./types";

type EstadoNavegacion = { radicadoToSelect?: string } | null | undefined;

/**
 * Selecciona el expediente que llega por `location.state.radicadoToSelect`
 * (notificaciones, alertas, informes) en cuanto la lista está cargada. Si no
 * está en la lista, activa `noDisponible` para mostrar el aviso.
 *
 * El state se limpia con `navigate(..., { replace: true })` para que un
 * refetch de la lista no vuelva a seleccionar el expediente; una navegación
 * nueva (aunque sea al mismo radicado) trae un state nuevo y vuelve a aplicar.
 *
 * `expedientes` es `undefined` mientras la lista no se ha cargado.
 */
export function useExpedienteDesdeNavegacion<T extends ExpedienteBase>(
  expedientes: T[] | undefined,
  seleccionar: (expediente: T) => void,
) {
  const location = useLocation();
  const navigate = useNavigate();
  const [noDisponible, setNoDisponible] = useState(false);
  const radicado = (location.state as EstadoNavegacion)?.radicadoToSelect;

  useEffect(() => {
    if (!radicado || !expedientes) return;
    const encontrado = expedientes.find((e) => e.radicado === radicado);
    if (encontrado) seleccionar(encontrado);
    else setNoDisponible(true);
    navigate(
      { pathname: location.pathname, search: location.search },
      { replace: true, state: null },
    );
  }, [radicado, expedientes, seleccionar, navigate, location.pathname, location.search]);

  return { noDisponible, cerrarAviso: () => setNoDisponible(false) };
}
