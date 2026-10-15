import { Filter, RefreshCw, X } from "lucide-react";
import CustomSelect from "@shared/ui/form/CustomSelect";
import { FILTROS_MIS_DOCUMENTOS, type FiltrosMisDocumentos } from "../../api/misDocumentos";
import { hayFiltrosActivos, type RolMisDocumentos } from "../../api/misDocumentosParams";
import type { FiltrosMisDocumentosOpciones } from "../../types";

type Props = {
  filtros: FiltrosMisDocumentos;
  onChange: (f: FiltrosMisDocumentos) => void;
  /** Opciones que manda el backend (`filtros` de B.2); no se hardcodean. */
  opciones: FiltrosMisDocumentosOpciones | undefined;
  onActualizar: () => void;
  actualizando: boolean;
};

/** Filtros de Mis informes (mismo aspecto que los de infraction). */
export default function MisDocumentosFiltros({ filtros, onChange, opciones, onActualizar, actualizando }: Props) {
  const activos = hayFiltrosActivos(filtros);
  const set = (parcial: Partial<FiltrosMisDocumentos>) => onChange({ ...filtros, ...parcial });

  return (
    <div className="card bg-base-100 shadow border border-base-300">
      <div className="card-body p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-semibold text-base-content/70 flex items-center gap-2">
            <Filter size={14} />
            Filtros de búsqueda
            {activos && <span className="badge badge-success badge-sm">activos</span>}
          </span>
          <div className="flex items-center gap-2">
            <button type="button" onClick={onActualizar} className="btn btn-ghost btn-xs gap-1" disabled={actualizando}>
              <RefreshCw size={12} className={actualizando ? "animate-spin" : ""} />
              Actualizar
            </button>
            <button
              type="button"
              onClick={() => onChange(FILTROS_MIS_DOCUMENTOS)}
              disabled={!activos}
              className={`btn btn-xs gap-1 ${activos ? "btn-error btn-outline" : "btn-ghost opacity-40"}`}
            >
              <X size={12} />
              Limpiar
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3">
          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium text-base-content/60">Expediente o radicado</span>
            <input
              type="text"
              placeholder="Ej: CA 012 o 2026ER..."
              className="input input-sm w-full"
              value={filtros.expediente}
              onChange={(e) => set({ expediente: e.target.value })}
            />
          </label>
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium text-base-content/60">Documento</span>
            <CustomSelect
              className="select-sm"
              value={filtros.tipo_documento}
              onChange={(tipo_documento) => set({ tipo_documento })}
              placeholder="Todos"
              emptyValue=""
              options={(opciones?.tipos_documento ?? []).map((t) => ({ value: t.codigo, label: t.etiqueta }))}
            />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium text-base-content/60">Mi rol</span>
            <CustomSelect
              className="select-sm"
              value={filtros.rol}
              onChange={(rol) => set({ rol: rol as RolMisDocumentos })}
              placeholder="Todos"
              emptyValue=""
              options={(opciones?.roles ?? []).map((r) => ({ value: r.codigo, label: r.etiqueta }))}
            />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium text-base-content/60">Estado</span>
            <CustomSelect
              className="select-sm"
              value={filtros.estado}
              onChange={(estado) => set({ estado })}
              placeholder="Todos"
              emptyValue=""
              options={(opciones?.estados ?? []).map((e) => ({ value: e.codigo, label: e.etiqueta }))}
            />
          </div>
          <label className="flex items-center gap-2 self-end pb-1 cursor-pointer">
            <input
              type="checkbox"
              className="checkbox checkbox-sm checkbox-info"
              checked={filtros.soloAccion}
              onChange={(e) => set({ soloAccion: e.target.checked })}
            />
            <span className="text-xs font-medium text-base-content/70">Solo los que requieren mi acción</span>
          </label>
        </div>
      </div>
    </div>
  );
}
