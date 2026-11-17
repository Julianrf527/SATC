import type { ReactNode } from "react";

// Tarjetas de estado comunes a las etapas, con el mismo marcado que
// infraction (modules/app-infraccion/etapas/EtapaEstados.tsx). Replicadas
// aquí porque un módulo no importa otro.

const ICONO_ESCUDO =
  "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z";
const ICONO_ALERTA =
  "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z";

function IconoEtapa({ d, className }: { d: string; className: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={d} />
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

/** Modo consulta: la etapa no existe. */
export function EtapaNoExiste({ etapa }: { etapa: string }) {
  return (
    <div className="card bg-base-100 shadow-xl w-full border border-base-300">
      <div className="card-body">
        <div className="flex flex-col items-center justify-center py-8 space-y-6">
          <div className="bg-gradient-to-br from-gray-400 to-gray-500 rounded-full p-4 shadow-lg">
            <IconoEtapa d={ICONO_ESCUDO} className="h-16 w-16 text-white" />
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

/** La etapa no existe y el backend dice que aún no se puede crear (motivo de bloqueo). */
export function EtapaNoCreable({ motivo, children }: { motivo: string | null; children?: ReactNode }) {
  return (
    <div className="card bg-base-100 shadow-xl w-full border border-warning/30">
      <div className="card-body">
        <div className="flex flex-col items-center justify-center py-8 space-y-6">
          <div className="bg-gradient-to-br from-warning to-orange-500 rounded-full p-4 shadow-lg">
            <IconoEtapa d={ICONO_ALERTA} className="h-16 w-16 text-white" />
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

/**
 * La etapa no existe pero se puede crear: descripción y las acciones que
 * mande el backend (asignarme, registrar radicado, cargue directo...). Mismo
 * marcado que `EtapaPorCrear` de infraction.
 */
export function EtapaPorCrear({
  etapa,
  descripcion,
  children,
}: {
  etapa: string;
  descripcion: string;
  children?: ReactNode;
}) {
  return (
    <div className="card bg-base-100 shadow-xl w-full border border-info/30">
      <div className="card-body">
        <div className="flex flex-col items-center justify-center py-8 space-y-6">
          <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-full p-4 shadow-lg">
            <IconoEtapa d={ICONO_ESCUDO} className="h-16 w-16 text-white" />
          </div>
          <div className="text-center space-y-3">
            <p className="text-base-content/70 max-w-md mx-auto">
              Este expediente aún no tiene la etapa de{" "}
              <span className="font-semibold text-tono-info whitespace-nowrap">"{etapa}"</span>.
            </p>
            <p className="text-sm text-base-content/70 max-w-md mx-auto">{descripcion}</p>
          </div>
          {children && <div className="flex flex-wrap items-center justify-center gap-3">{children}</div>}
        </div>
      </div>
    </div>
  );
}
