import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { API_CONFIG, apiCall } from "../../../utils/api";
import type { ModeloGenerico } from "../../../types/common";

export type FilterData = {
  motivo_afectacion?: string;
  direccion?: string;
  municipio_id?: number;
  vereda_ids?: number[];
  recurso_ids?: number[];
  valor_exacto: boolean;
};

type Props = {
  isOpen: boolean;
  onClose: (isOpen: boolean) => void;
  onApplyFilters: (filters: FilterData) => void;
  municipioList: ModeloGenerico[];
  recursoAfectadoList: ModeloGenerico[];
};

export default function AdvancedFiltersModal({
  isOpen,
  onClose,
  onApplyFilters,
  municipioList,
  recursoAfectadoList,
}: Props) {
  const getInitialTheme = () =>
    document.querySelector("[data-theme]")?.getAttribute("data-theme") || "emerald";

  const [theme, setTheme] = useState<string>(getInitialTheme);
  const [filters, setFilters] = useState<FilterData>({ valor_exacto: false });
  const [veredas, setVeredas] = useState<ModeloGenerico[]>([]);
  const [loadingVeredas, setLoadingVeredas] = useState(false);

  useEffect(() => {
    const updateTheme = () => {
      const currentTheme =
        document.querySelector("[data-theme]")?.getAttribute("data-theme") || "emerald";
      setTheme(currentTheme);
    };
    updateTheme();
    const observer = new MutationObserver(updateTheme);
    const targetNode = document.querySelector("[data-theme]");
    if (targetNode) observer.observe(targetNode, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!filters.municipio_id) {
      setVeredas([]);
      return;
    }
    setLoadingVeredas(true);
    apiCall(API_CONFIG.ENDPOINTS.TOWNS_SIDEWALK_BY_TOWN(filters.municipio_id))
      .then((r) => { if (r.ok) setVeredas(r.veredas || []); })
      .catch(() => {})
      .finally(() => setLoadingVeredas(false));
  }, [filters.municipio_id]);

  const handleToggleVereda = (id: number) =>
    setFilters((prev) => {
      const cur = prev.vereda_ids || [];
      return { ...prev, vereda_ids: cur.includes(id) ? cur.filter((v) => v !== id) : [...cur, id] };
    });

  const handleToggleRecurso = (id: number) =>
    setFilters((prev) => {
      const cur = prev.recurso_ids || [];
      return { ...prev, recurso_ids: cur.includes(id) ? cur.filter((v) => v !== id) : [...cur, id] };
    });

  const handleClearFilters = () => { setFilters({ valor_exacto: false }); setVeredas([]); };
  const handleClose = () => onClose(!isOpen);

  const handleApply = () => {
    const clean: Partial<FilterData> = {};
    if (filters.motivo_afectacion) clean.motivo_afectacion = filters.motivo_afectacion;
    if (filters.direccion) clean.direccion = filters.direccion;
    if (filters.municipio_id) clean.municipio_id = filters.municipio_id;
    if (filters.vereda_ids?.length) clean.vereda_ids = filters.vereda_ids;
    if (filters.recurso_ids?.length) clean.recurso_ids = filters.recurso_ids;
    clean.valor_exacto = filters.valor_exacto;
    onApplyFilters(clean as FilterData);
    onClose(!isOpen);
  };

  if (!isOpen) return null;

  const activeFiltersCount = Object.entries(filters).filter(([key, value]) => {
    if (key === "valor_exacto") return false;
    if (!value) return false;
    if (Array.isArray(value) && value.length === 0) return false;
    return true;
  }).length;

  return createPortal(
    <div
      data-theme={theme}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
    >
      <div className="bg-base-100 rounded-2xl w-full max-w-2xl mx-4 shadow-2xl border border-base-300 max-h-[90vh] flex flex-col">

        {/* Header */}
        <div className="px-6 py-4 border-b border-base-300 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-success/10 rounded-xl flex items-center justify-center">
              <svg className="w-4 h-4 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L13 13.414V19a1 1 0 01-.553.894l-4 2A1 1 0 017 21v-7.586L3.293 6.707A1 1 0 013 6V4z" />
              </svg>
            </div>
            <div>
              <h3 className="font-bold text-base text-base-content">Filtros Avanzados</h3>
              <p className="text-xs text-base-content/50">
                {activeFiltersCount > 0
                  ? `${activeFiltersCount} filtro${activeFiltersCount > 1 ? "s" : ""} activo${activeFiltersCount > 1 ? "s" : ""}`
                  : "Búsqueda en base de datos"}
              </p>
            </div>
          </div>
          <button onClick={handleClose} className="btn btn-ghost btn-sm btn-circle">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">

          {/* Información del expediente */}
          <div>
            <p className="text-xs font-semibold text-base-content/50 uppercase tracking-wider mb-3">
              Información del expediente
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="form-control">
                <label className="label py-1">
                  <span className="label-text text-sm">Motivo de afectación</span>
                </label>
                <input
                  type="text"
                  className="input input-sm input-bordered"
                  placeholder="Buscar por motivo..."
                  value={filters.motivo_afectacion || ""}
                  onChange={(e) => setFilters((p) => ({ ...p, motivo_afectacion: e.target.value }))}
                />
              </div>
              <div className="form-control">
                <label className="label py-1">
                  <span className="label-text text-sm">Dirección</span>
                </label>
                <input
                  type="text"
                  className="input input-sm input-bordered"
                  placeholder="Buscar por dirección..."
                  value={filters.direccion || ""}
                  onChange={(e) => setFilters((p) => ({ ...p, direccion: e.target.value }))}
                />
              </div>
            </div>
          </div>

          <div className="divider my-0" />

          {/* Ubicación */}
          <div>
            <p className="text-xs font-semibold text-base-content/50 uppercase tracking-wider mb-3">
              Ubicación
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="form-control">
                <label className="label py-1">
                  <span className="label-text text-sm">Municipio</span>
                </label>
                <select
                  className="select select-sm select-bordered"
                  value={filters.municipio_id || ""}
                  onChange={(e) => {
                    const val = e.target.value;
                    if (val) {
                      setFilters((p) => ({ ...p, municipio_id: Number(val), vereda_ids: [] }));
                    } else {
                      setFilters((p) => { const n = { ...p }; delete n.municipio_id; delete n.vereda_ids; return n; });
                    }
                  }}
                >
                  <option value="">Todos los municipios</option>
                  {municipioList.map((m) => (
                    <option key={m.id} value={m.id}>{m.nombre}</option>
                  ))}
                </select>
              </div>

              {filters.municipio_id && (
                <div className="form-control">
                  <label className="label py-1">
                    <span className="label-text text-sm flex items-center gap-1">
                      Veredas
                      {loadingVeredas && <span className="loading loading-spinner loading-xs" />}
                      {(filters.vereda_ids?.length ?? 0) > 0 && (
                        <span className="badge badge-success badge-xs">{filters.vereda_ids!.length}</span>
                      )}
                    </span>
                  </label>
                  <div className="border border-base-300 rounded-lg max-h-32 overflow-y-auto bg-base-50">
                    {loadingVeredas ? (
                      <div className="flex justify-center py-4">
                        <span className="loading loading-spinner loading-sm" />
                      </div>
                    ) : veredas.length === 0 ? (
                      <p className="text-xs text-base-content/50 text-center py-4">Sin veredas</p>
                    ) : (
                      veredas.map((v) => (
                        <label key={v.id} className="flex items-center gap-2 cursor-pointer hover:bg-base-200 px-3 py-1.5">
                          <input
                            type="checkbox"
                            className="checkbox checkbox-success checkbox-xs"
                            checked={filters.vereda_ids?.includes(v.id) || false}
                            onChange={() => handleToggleVereda(v.id)}
                          />
                          <span className="text-xs">{v.nombre}</span>
                        </label>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="divider my-0" />

          {/* Recursos afectados */}
          <div>
            <p className="text-xs font-semibold text-base-content/50 uppercase tracking-wider mb-3">
              Recursos afectados
              {(filters.recurso_ids?.length ?? 0) > 0 && (
                <span className="badge badge-success badge-xs ml-2">{filters.recurso_ids!.length}</span>
              )}
            </p>
            <div className="border border-base-300 rounded-lg max-h-32 overflow-y-auto">
              {recursoAfectadoList.map((r) => (
                <label key={r.id} className="flex items-center gap-2 cursor-pointer hover:bg-base-200 px-3 py-1.5">
                  <input
                    type="checkbox"
                    className="checkbox checkbox-success checkbox-xs"
                    checked={filters.recurso_ids?.includes(r.id) || false}
                    onChange={() => handleToggleRecurso(r.id)}
                  />
                  <span className="text-sm">{r.nombre}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="divider my-0" />

          {/* Modo de búsqueda */}
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              className="checkbox checkbox-success checkbox-sm"
              checked={filters.valor_exacto}
              onChange={(e) => setFilters((p) => ({ ...p, valor_exacto: e.target.checked }))}
            />
            <div>
              <span className="text-sm font-medium text-base-content">Búsqueda exacta</span>
              <p className="text-xs text-base-content/50">Coincidencias exactas en lugar de parciales</p>
            </div>
          </label>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-base-300 flex items-center justify-between gap-3 flex-shrink-0">
          <button
            onClick={handleClearFilters}
            className="btn btn-ghost btn-sm gap-1"
            disabled={activeFiltersCount === 0}
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
            Limpiar
          </button>
          <div className="flex gap-2">
            <button onClick={handleClose} className="btn btn-ghost btn-sm">Cancelar</button>
            <button onClick={handleApply} className="btn btn-success btn-sm text-white gap-1.5">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              Buscar
              {activeFiltersCount > 0 && (
                <span className="badge badge-sm bg-white/20 text-white border-0">{activeFiltersCount}</span>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}
