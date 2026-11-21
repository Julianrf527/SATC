import { useState } from "react";
import { useLocation } from "react-router-dom";

type EstadoNavegacion = { radicadoToSelect?: string; etapaToSelect?: string } | null | undefined;

/**
 * Pestaña de etapa con la que abrir el expediente que llega por navegación
 * ("Ir a la etapa" desde Mis actuaciones: `{ radicadoToSelect, etapaToSelect }`).
 * Se captura al montar porque `useExpedienteDesdeNavegacion` limpia el state
 * en cuanto selecciona el expediente; solo aplica a ESE expediente.
 */
export function useEtapaDesdeNavegacion(radicadoSeleccionado: string | null | undefined): string | null {
  const location = useLocation();
  const [destino] = useState(() => {
    const state = location.state as EstadoNavegacion;
    return state?.radicadoToSelect && state.etapaToSelect
      ? { radicado: state.radicadoToSelect, etapa: state.etapaToSelect }
      : null;
  });
  return destino && destino.radicado === radicadoSeleccionado ? destino.etapa : null;
}
