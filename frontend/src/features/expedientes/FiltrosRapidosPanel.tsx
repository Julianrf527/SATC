import { useState } from "react";
import { ChevronDown, Search, SlidersHorizontal, X } from "lucide-react";
import CustomSelect from "@shared/ui/form/CustomSelect";
import CustomDateInput from "@shared/ui/form/CustomDateInput";
import type { FiltrosRapidosState } from "./useFiltrosRapidos";

type Props = {
  filtros: FiltrosRapidosState;
  /** Hay una búsqueda avanzada (BD) aplicada. */
  avanzadoActivo: boolean;
  onAbrirAvanzado: () => void;
  onLimpiarTodo: () => void;
};

/** Cabecera de la lista: búsqueda por radicado, filtros rápidos y acceso al avanzado. */
export default function FiltrosRapidosPanel({
  filtros,
  avanzadoActivo,
  onAbrirAvanzado,
  onLimpiarTodo,
}: Props) {
  const [abiertos, setAbiertos] = useState(false);

  return (
    <div className="flex-shrink-0 p-6 border-b border-base-300 bg-base-100">
      <h2 className="text-2xl font-bold text-base-content mb-4">Expedientes</h2>

      {/* Filtro principal - Radicado */}
      <div className="relative">
        <input
          className="w-full input"
          placeholder="Buscar por radicado..."
          type="text"
          value={filtros.radicado}
          onChange={(e) => filtros.setRadicado(e.target.value)}
        />
        <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-base-content/40" />
      </div>

      {/* Botones de filtros */}
      <div className="mt-3 flex gap-2">
        <button
          onClick={() => setAbiertos(!abiertos)}
          className="btn btn-ghost btn-sm flex-1 justify-between"
        >
          <span className="flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4" />
            Rápidos
          </span>
          <ChevronDown
            className={`w-4 h-4 transition-transform ${abiertos ? "rotate-180" : "rotate-0"}`}
          />
        </button>

        <button
          onClick={onAbrirAvanzado}
          className={`btn btn-sm flex-1 gap-2 ${
            avanzadoActivo ? "btn-success text-white" : "btn-outline"
          }`}
        >
          <Search className="w-4 h-4" />
          Avanzados
          {avanzadoActivo && (
            <span className="badge badge-sm bg-white text-success">BD</span>
          )}
        </button>
      </div>

      {/* Filtros rápidos colapsables */}
      <div className={`${abiertos ? "block" : "hidden"} mt-4 space-y-3`}>
        <input
          className="input input-sm w-full"
          placeholder="Nombre o documento"
          type="text"
          value={filtros.nombre}
          onChange={(e) => filtros.setNombre(e.target.value)}
        />

        <div className="grid grid-cols-2 gap-2">
          <CustomDateInput
            className="input-sm"
            placeholder="Fecha desde"
            value={filtros.desde}
            onChange={filtros.setDesde}
          />
          <CustomDateInput
            className="input-sm"
            placeholder="Fecha hasta"
            value={filtros.hasta}
            onChange={filtros.setHasta}
          />
        </div>

        {filtros.selects.map((s) => (
          <CustomSelect
            key={s.id}
            className="select-sm"
            hidePlaceholderOption
            value={s.valor}
            onChange={(v: string) => filtros.setSeleccion(s.id, v)}
            options={s.opciones}
          />
        ))}
      </div>

      {(filtros.hayActivos || avanzadoActivo) && (
        <button onClick={onLimpiarTodo} className="btn btn-sm btn-ghost w-full mt-3 gap-2">
          <X className="w-4 h-4" />
          Limpiar todos los filtros
        </button>
      )}
    </div>
  );
}
