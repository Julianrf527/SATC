import { BellRing } from "lucide-react";
import { EstadoBadge } from "@shared/ui";
import type { ResumenProcesoInforme } from "../types";

type Props = {
  informe: ResumenProcesoInforme & { aceptado: boolean; profesional_asignado_id?: number | null };
};

/**
 * Estado de un informe en los listados. Un informe aceptado (por flujo o
 * cargue manual) se muestra "Aceptado"; si no, el estado del proceso llega ya
 * con etiqueta y tono (`estado_proceso`), y aquí solo se resuelve lo que no
 * tiene proceso (sin asignar, sin proceso).
 */
export default function EstadoInformeBadge({ informe }: Props) {
  const estado = informe.estado_proceso;
  return (
    <div className="flex flex-wrap items-center gap-1">
      {informe.aceptado ? (
        <EstadoBadge etiqueta="Aceptado" tono="success" />
      ) : estado ? (
        <EstadoBadge etiqueta={estado.etiqueta} tono={estado.tono} />
      ) : informe.profesional_asignado_id === null ? (
        <EstadoBadge etiqueta="Sin asignar" tono="error" />
      ) : (
        <EstadoBadge etiqueta="Sin proceso" tono="neutral" />
      )}
      {informe.requiere_mi_accion && (
        <EstadoBadge etiqueta="Tu turno" tono="info" icono={<BellRing size={11} />} title="Requiere tu acción" />
      )}
    </div>
  );
}

