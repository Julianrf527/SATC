import type { ReactNode } from "react";
import type { Creable } from "../../types";
import Icono from "./Icono";
import { ICONOS } from "./iconos";

type Props = {
  expedienteId: number;
  /** Nombre de la etapa en mayúsculas ("CESACION"); se muestra entre comillas. */
  nombreEtapa: string;
  /** "Obteniendo información de ..." en el spinner de carga. */
  textoCarga: string;
  /** Texto bajo el título de la tarjeta "crear etapa". */
  textoCrear: string;
  /** Trazo del icono grande de las tarjetas "sin etapa" (por defecto documento). */
  icono?: string;
  isEditable: boolean;
  cargando: boolean;
  /** true cuando la carga tarda más de 300 ms (evita parpadeos). */
  mostrarCarga: boolean;
  etapaExiste: boolean;
  creable: Creable;
  creando: boolean;
  onCrear: () => void;
  /** Contenido extra bajo el botón "Crear Etapa" (p. ej. importar desde infracciones). */
  extraCrear?: ReactNode;
  /** Contenido de la etapa cuando existe. */
  children: ReactNode;
};

/**
 * Estados comunes de una etapa del proceso sancionatorio: cargando, sin
 * expediente, no creable, sin etapa (solo lectura / crear) y contenido.
 * Lo específico de cada etapa entra por textos, icono y slots.
 */
export default function EtapaContenedor({
  expedienteId,
  nombreEtapa,
  textoCarga,
  textoCrear,
  icono = ICONOS.documento,
  isEditable,
  cargando,
  mostrarCarga,
  etapaExiste,
  creable,
  creando,
  onCrear,
  extraCrear,
  children,
}: Props) {
  if (cargando && mostrarCarga) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-base-300">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-12 space-y-4">
            <span className="loading loading-spinner loading-lg text-primary"></span>
            <p className="text-base-content/70 font-medium">Cargando datos...</p>
            <p className="text-sm text-base-content/70">{textoCarga}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!expedienteId) {
    return (
      <div className="card bg-base-100 shadow w-full">
        <div className="card-body flex items-center justify-center text-base-content/70">
          <p>
            Seleccione un expediente para ver {isEditable ? "o editar" : ""} sus
            datos
          </p>
        </div>
      </div>
    );
  }

  // Aún cargando pero sin pasar el retardo: contenedor vacío.
  if (cargando) return <div className="min-h-[200px]" />;

  if (!creable.status && isEditable) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-warning/30">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-8 space-y-6">
            <div className="bg-gradient-to-br from-warning to-orange-500 rounded-full p-4 shadow-lg">
              <Icono d={ICONOS.alerta} className="h-16 w-16 text-white" />
            </div>
            <div className="text-center space-y-3">
              <h3 className="text-lg font-semibold">
                No es posible gestionar o crear esta etapa
              </h3>
              <div className="bg-warning/10 border border-warning/30 rounded-lg p-4 max-w-lg mx-auto">
                <p className="text-sm font-medium">
                  <span className="font-semibold text-tono-warning">Motivo:</span>{" "}
                  {creable.msg}
                </p>
              </div>
              <p className="text-sm opacity-70 max-w-md mx-auto mt-4">
                Por favor, complete los requisitos necesarios antes de crear
                esta etapa.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!etapaExiste && !isEditable) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-base-300">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-8 space-y-6">
            <div className="bg-gradient-to-br from-gray-400 to-gray-500 rounded-full p-4 shadow-lg">
              <Icono d={icono} className="h-16 w-16 text-white" />
            </div>
            <div className="text-center space-y-3">
              <p className="text-base-content/70 max-w-md mx-auto">
                Este expediente aún no tiene la etapa de{" "}
                <span className="font-semibold text-base-content whitespace-nowrap">
                  "{nombreEtapa}"
                </span>
                .
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

  if (!etapaExiste) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-info/30">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-8 space-y-6">
            <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-full p-4 shadow-lg">
              <Icono d={icono} className="h-16 w-16 text-white" />
            </div>
            <div className="text-center space-y-3">
              <p className="text-base-content/70 max-w-md mx-auto">
                Este expediente aún no tiene la etapa de{" "}
                <span className="font-semibold text-tono-info whitespace-nowrap">
                  "{nombreEtapa}"
                </span>
                .
              </p>
              <p className="text-sm text-base-content/70 max-w-md mx-auto">{textoCrear}</p>
            </div>
            <button
              className="btn btn-success text-white btn-lg gap-2 shadow-md hover:shadow-lg transition-all"
              onClick={onCrear}
              disabled={creando}
            >
              {creando ? (
                <>
                  <span className="loading loading-spinner loading-sm"></span>
                  Creando etapa...
                </>
              ) : (
                <>
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Crear Etapa
                </>
              )}
            </button>
            {extraCrear}
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
