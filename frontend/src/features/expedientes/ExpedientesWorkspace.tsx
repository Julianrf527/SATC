import { useState, type ReactNode } from "react";
import { ChevronRight } from "lucide-react";

type Props = {
  /** Panel lateral (normalmente el `ExpedienteList` del módulo). */
  lista: ReactNode;
  /** Contenido principal (detalle del expediente seleccionado). */
  detalle: ReactNode;
  /** Mientras carga se pinta solo el spinner a pantalla completa. */
  cargando?: boolean;
};

/**
 * Estructura de las pantallas de gestión / consulta de expedientes: lista
 * lateral plegable + detalle. Lo propio de cada módulo entra por los slots.
 */
export default function ExpedientesWorkspace({ lista, detalle, cargando = false }: Props) {
  const [mostrarLista, setMostrarLista] = useState(true);

  if (cargando) {
    return (
      <div className="flex h-[calc(100vh-4rem)] bg-base-200">
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <span className="loading loading-spinner loading-lg text-success"></span>
            <p className="text-base-content font-medium">Cargando expedientes...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-base-200">
      <div
        className={`${
          mostrarLista ? "w-80" : "w-0"
        } transition-all duration-300 ease-in-out overflow-hidden bg-base-100 shadow-lg border-r border-base-300`}
      >
        <div className="h-full">{lista}</div>
      </div>

      <div
        className="relative flex items-center justify-center bg-base-300 hover:bg-base-content/20 transition-colors duration-200"
        style={{ width: "2px" }}
      >
        <button
          type="button"
          onClick={() => setMostrarLista((v) => !v)}
          aria-label={mostrarLista ? "Ocultar lista de expedientes" : "Mostrar lista de expedientes"}
          aria-expanded={mostrarLista}
          className="absolute w-8 h-12 bg-base-100 hover:bg-base-200 shadow-md border border-base-300 rounded-md flex items-center justify-center transition-all duration-200 hover:shadow-lg hover:scale-105 z-10"
        >
          <ChevronRight
            size={16}
            strokeWidth={2.5}
            className={`text-base-content/70 transition-transform duration-300 ${
              mostrarLista ? "rotate-180" : "rotate-0"
            }`}
          />
        </button>
      </div>

      <div className="flex-1 overflow-hidden bg-base-200 flex flex-col">
        <div className="flex-1 overflow-hidden">{detalle}</div>
      </div>
    </div>
  );
}
