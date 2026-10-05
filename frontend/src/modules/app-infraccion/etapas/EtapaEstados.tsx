import type { ReactNode } from "react";
import { ICONOS_ETAPA } from "./iconosEtapa";

// Tarjetas de estado comunes a las etapas (Respuesta, Concepto, Cierre):
// cargando, sin expediente, etapa inexistente (consulta), etapa no creable y
// etapa por crear. Antes cada etapa repetía el mismo marcado.


export function IconoEtapa({ d, className }: { d: string; className: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={d} />
    </svg>
  );
}

export function IconoMas() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
      <path
        fillRule="evenodd"
        d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
        clipRule="evenodd"
      />
    </svg>
  );
}

export function EtapaCargando({ etapa }: { etapa: string }) {
  return (
    <div className="card bg-base-100 shadow-xl w-full border border-base-300">
      <div className="card-body">
        <div className="flex flex-col items-center justify-center py-12 space-y-4">
          <span className="loading loading-spinner loading-lg text-primary" />
          <p className="text-base-content/70 font-medium">Cargando datos...</p>
          <p className="text-sm text-base-content/70">
            Obteniendo información de la etapa {etapa}. Esto puede tardar unos segundos.
          </p>
        </div>
      </div>
    </div>
  );
}

export function EtapaSinExpediente({ isEditable }: { isEditable: boolean }) {
  return (
    <div className="card bg-base-100 shadow w-full">
      <div className="card-body flex items-center justify-center text-base-content/70">
        <p>Seleccione un expediente para ver{isEditable ? " o editar" : ""} sus datos</p>
      </div>
    </div>
  );
}

/** Hueco mientras carga, antes de que aparezca el spinner (evita parpadeo). */
export function EtapaHueco() {
  return <div className="min-h-[200px]" />;
}

/** Modo consulta: la etapa no existe. */
export function EtapaNoExiste({ etapa }: { etapa: string }) {
  return (
    <div className="card bg-base-100 shadow-xl w-full border border-base-300">
      <div className="card-body">
        <div className="flex flex-col items-center justify-center py-8 space-y-6">
          <div className="bg-gradient-to-br from-gray-400 to-gray-500 rounded-full p-4 shadow-lg">
            <IconoEtapa d={ICONOS_ETAPA.escudo} className="h-16 w-16 text-white" />
          </div>
          <div className="text-center space-y-3">
            <p className="text-base-content/70 max-w-md mx-auto">
              Este expediente aún no tiene la etapa de{" "}
              <span className="font-semibold text-base-content whitespace-nowrap">"{etapa}"</span>.
            </p>
            <p className="text-sm text-base-content/70 max-w-md mx-auto">
              No hay información disponible para visualizar en esta etapa.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

/** La etapa no existe y el backend dice que aún no se puede crear. */
export function EtapaNoCreable({ motivo, children }: { motivo: string | null; children?: ReactNode }) {
  return (
    <div className="card bg-base-100 shadow-xl w-full border border-warning/30">
      <div className="card-body">
        <div className="flex flex-col items-center justify-center py-8 space-y-6">
          <div className="bg-gradient-to-br from-warning to-orange-500 rounded-full p-4 shadow-lg">
            <IconoEtapa d={ICONOS_ETAPA.alerta} className="h-16 w-16 text-white" />
          </div>
          <div className="text-center space-y-3">
            <h3 className="text-lg font-semibold">No es posible gestionar o crear esta etapa</h3>
            <div className="bg-warning/10 border border-warning/30 rounded-lg p-4 max-w-lg mx-auto">
              <p className="text-sm font-medium">
                <span className="font-semibold text-tono-warning">Motivo:</span>{" "}
                {motivo ?? "No se cumplen los requisitos para crear esta etapa"}
              </p>
            </div>
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}

type EtapaPorCrearProps = {
  etapa: string;
  /** Path del icono grande. */
  icono: string;
  descripcion: string;
  /** Color del nombre de la etapa (cada etapa usaba un tono distinto). */
  etapaClassName?: string;
  /** Botón de crear. */
  children: ReactNode;
};

/** La etapa no existe y se puede crear. */
export function EtapaPorCrear({
  etapa,
  icono,
  descripcion,
  etapaClassName = "text-tono-info",
  children,
}: EtapaPorCrearProps) {
  return (
    <div className="card bg-base-100 shadow-xl w-full border border-info/30">
      <div className="card-body">
        <div className="flex flex-col items-center justify-center py-8 space-y-6">
          <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-full p-4 shadow-lg">
            <IconoEtapa d={icono} className="h-16 w-16 text-white" />
          </div>
          <div className="text-center space-y-3">
            <p className="text-base-content/70 max-w-md mx-auto">
              Este expediente aún no tiene la etapa de{" "}
              <span className={`font-semibold ${etapaClassName} whitespace-nowrap`}>"{etapa}"</span>.
            </p>
            <p className="text-sm text-base-content/70 max-w-md mx-auto">{descripcion}</p>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}
