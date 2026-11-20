import type { ReactNode } from "react";
import { ETAPAS_PROCESO, TITULO_ETAPA, type CodigoEtapa } from "../manage/etapasProceso";

type Props = {
  etapa: CodigoEtapa;
  /** Badges / botones de la etapa (derecha de la cabecera). */
  acciones?: ReactNode;
  children: ReactNode;
};

/**
 * Recuadro de una etapa, como el nodo de etapa de recurso: "Etapa N · Nombre"
 * en la cabecera y TODO el contenido de la etapa adentro. Las tarjetas
 * internas pierden la sombra y quedan como recuadros anidados.
 */
export default function TarjetaEtapa({ etapa, acciones, children }: Props) {
  const icono = ETAPAS_PROCESO.find((e) => e.codigo === etapa)?.icono ?? "bx-file";
  return (
    <div className="card bg-base-100 shadow-md border border-base-300">
      <div className="card-body">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-2">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-info/10 text-info">
              <i className={`bx ${icono} text-xl`}></i>
            </div>
            <h3 className="text-xl font-bold">{TITULO_ETAPA[etapa]}</h3>
          </div>
          {acciones && <div className="flex flex-wrap items-center gap-2">{acciones}</div>}
        </div>
        <div className="space-y-6 [&_.card]:shadow-none">{children}</div>
      </div>
    </div>
  );
}
