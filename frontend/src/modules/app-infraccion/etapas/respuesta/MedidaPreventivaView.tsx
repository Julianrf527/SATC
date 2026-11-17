import type { ReactNode } from "react";
import type { MedidaInfo, TipoMedida } from "../../types";

function getEstadoLabel(estado: boolean | null) {
  if (estado === null) return "No Aplica";
  return estado ? "Vigente" : "Levantada";
}

function getEstadoBadgeClass(estado: boolean | null) {
  if (estado === null) return "badge-ghost";
  return estado ? "badge-success" : "badge-warning";
}

function Dato({ icono, etiqueta, children }: { icono: string; etiqueta: string; children: ReactNode }) {
  return (
    <div className="flex items-start gap-3">
      <div className="w-8 h-8 bg-base-200 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
        <svg className="w-4 h-4 text-base-content/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={icono} />
        </svg>
      </div>
      <div>
        <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">{etiqueta}</p>
        {children}
      </div>
    </div>
  );
}

/** Vista de los datos de la medida preventiva registrada. */
export default function MedidaPreventivaView({
  medidaInfo,
  tipoMedidas,
}: {
  medidaInfo: MedidaInfo;
  tipoMedidas: TipoMedida[];
}) {
  return (
    <div className="border border-base-300 rounded-xl p-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <Dato
            etiqueta="Tipo de Medida"
            icono="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
          >
            <p className="text-sm font-semibold">
              {tipoMedidas.find((t) => t.id === medidaInfo.tipo_medida_id)?.nombre ?? "—"}
            </p>
          </Dato>
          <Dato etiqueta="Cantidad" icono="M7 20l4-16m2 16l4-16M6 9h14M4 15h14">
            <p className="text-sm">{medidaInfo.cantidad}</p>
          </Dato>
        </div>
        <div className="space-y-4">
          <Dato
            etiqueta="Especie"
            icono="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
          >
            <p className="text-sm">{medidaInfo.especie}</p>
          </Dato>
          <Dato etiqueta="Estado" icono="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z">
            <span className={`badge text-white ${getEstadoBadgeClass(medidaInfo.estado_medida)} badge-sm mt-1`}>
              {getEstadoLabel(medidaInfo.estado_medida)}
            </span>
          </Dato>
        </div>
      </div>
    </div>
  );
}
