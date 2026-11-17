import { useState } from "react";
import { Filter, RefreshCw, Search, X } from "lucide-react";
import CustomDateInput from "@shared/ui/form/CustomDateInput";
import CustomSelect from "@shared/ui/form/CustomSelect";
import type { EstadoProceso } from "@features/proceso-revision";
import type { FiltrosDocumentos } from "../types";

type Props = {
  filtros: FiltrosDocumentos;
  /** Catálogo de estados que manda /docs/list (no se mantiene en el frontend). */
  estados: EstadoProceso[];
  onFiltros: (f: FiltrosDocumentos) => void;
  busqueda: string;
  onBusqueda: (texto: string) => void;
  onLimpiar: () => void;
  onActualizar: () => void;
  actualizando: boolean;
};

export default function DocumentosFiltros({
  filtros,
  estados,
  onFiltros,
  busqueda,
  onBusqueda,
  onLimpiar,
  onActualizar,
  actualizando,
}: Props) {
  const [abiertos, setAbiertos] = useState(false);
  const activos = !!(filtros.estado || filtros.fechaDesde || filtros.fechaHasta || busqueda);

  return (
    <div className="bg-base-100 rounded-lg p-4 shadow-sm border border-base-300 mb-6">
      <div className="flex flex-col md:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-base-content/60" size={18} />
          <input
            type="text"
            aria-label="Buscar por nombre de documento"
            placeholder="Buscar por nombre de documento..."
            value={busqueda}
            onChange={(e) => onBusqueda(e.target.value)}
            className="input w-full pl-10"
          />
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setAbiertos(!abiertos)}
            className={`btn ${abiertos ? "btn-success" : "btn-ghost"} gap-2`}
            aria-expanded={abiertos}
          >
            <Filter size={18} />
            Filtros
            {activos && <span className="badge badge-success badge-sm">●</span>}
          </button>
          <button type="button" onClick={onActualizar} className="btn btn-ghost gap-2" disabled={actualizando}>
            <RefreshCw size={18} className={actualizando ? "animate-spin" : ""} />
            Actualizar
          </button>
        </div>
      </div>

      {abiertos && (
        <div className="mt-4 pt-4 border-t border-base-300">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <span className="block text-sm font-medium text-base-content/70 mb-1">Estado</span>
              <CustomSelect
                value={filtros.estado}
                onChange={(estado) => onFiltros({ ...filtros, estado })}
                emptyValue=""
                placeholder="Todos los estados"
                options={estados.map((e) => ({ value: e.codigo, label: e.etiqueta }))}
              />
            </div>
            <div>
              <span className="block text-sm font-medium text-base-content/70 mb-1">Fecha Desde</span>
              <CustomDateInput
                value={filtros.fechaDesde}
                onChange={(fechaDesde) => onFiltros({ ...filtros, fechaDesde })}
              />
            </div>
            <div>
              <span className="block text-sm font-medium text-base-content/70 mb-1">Fecha Hasta</span>
              <CustomDateInput
                value={filtros.fechaHasta}
                onChange={(fechaHasta) => onFiltros({ ...filtros, fechaHasta })}
              />
            </div>
          </div>
          {activos && (
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={onLimpiar}
                className="btn btn-ghost btn-sm gap-2"
              >
                <X size={16} />
                Limpiar Filtros
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
