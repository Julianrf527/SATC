import type { ReactNode } from "react";
import type { NodoEtapa } from "../../types";
import { EtapaNoCreable, EtapaNoExiste, EtapaPorCrear } from "../EtapaEstados";

type Props = {
  nodo: Pick<NodoEtapa<unknown>, "existe" | "habilitada" | "motivos_bloqueo">;
  etapa: string;
  isEditable: boolean;
  /** Qué hacer para crearla (cuando está habilitada). */
  descripcion: string;
  /** Botones para crear la etapa (según `acciones_disponibles`). */
  crear?: ReactNode;
  /** Contenido de la etapa cuando existe. */
  children: ReactNode;
};

/**
 * Estado vacío de una pestaña, como en infraction: en Consulta "no existe";
 * bloqueada → motivo(s) de §6 que manda el backend; habilitada → acciones
 * para crearla. Si existe, pinta la etapa.
 */
export default function EtapaRaiz({ nodo, etapa, isEditable, descripcion, crear, children }: Props) {
  if (nodo.existe) return <>{children}</>;
  if (!isEditable) return <EtapaNoExiste etapa={etapa} />;
  if (!nodo.habilitada) {
    return (
      <EtapaNoCreable motivo={nodo.motivos_bloqueo.join(" · ") || null}>
        {crear && <div className="flex flex-wrap justify-center gap-2 pt-2">{crear}</div>}
      </EtapaNoCreable>
    );
  }
  return (
    <EtapaPorCrear etapa={etapa} descripcion={descripcion}>
      {crear}
    </EtapaPorCrear>
  );
}
