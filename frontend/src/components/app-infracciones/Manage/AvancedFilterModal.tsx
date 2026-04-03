import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { API_CONFIG, apiCall } from "../../../utils/api";
import type { ModeloGenerico, Municipio } from "../../../types/common";

type Props = {
  isOpen: boolean;
  onClose: (isOpen: boolean) => void;
  onApplyFilters: (filters: FilterData) => void;
  municipioList: Municipio[];
  recursoAfectadoList: ModeloGenerico[];
};

export type FilterData = {
  motivo_afectacion?: string;
  direccion?: string;
  municipio_id?: number;
  vereda_ids?: number[];
  recurso_ids?: number[];
  valor_exacto: boolean;
};

export default function AdvancedFiltersModal({
  isOpen,
  onClose,
  onApplyFilters,
  municipioList,
  recursoAfectadoList,
}: Props) {
  const getInitialTheme = () =>
    document.querySelector("[data-theme]")?.getAttribute("data-theme") ||
    "emerald";

  const [theme, setTheme] = useState<string>(getInitialTheme);

  const [filters, setFilters] = useState<FilterData>({
    valor_exacto: false,
  });

  const [veredas, setVeredas] = useState<ModeloGenerico[]>([]);
  const [loadingVeredas, setLoadingVeredas] = useState(false);
  const [activeSection, setActiveSection] = useState<string | null>(null);

  // Detectar el tema actual del documento
  useEffect(() => {
    const updateTheme = () => {
      const currentTheme =
        document.querySelector("[data-theme]")?.getAttribute("data-theme") ||
        "emerald";
      setTheme(currentTheme);
    };

    updateTheme();

    const observer = new MutationObserver(updateTheme);
    const targetNode = document.querySelector("[data-theme]");

    if (targetNode) {
      observer.observe(targetNode, {
        attributes: true,
        attributeFilter: ["data-theme"],
      });
    }

    return () => observer.disconnect();
  }, []);

  // Cargar veredas cuando se selecciona un municipio
  useEffect(() => {
    const fetchVeredas = async () => {
      if (!filters.municipio_id) {
        setVeredas([]);
        return;
      }

      setLoadingVeredas(true);
      try {
        const response = await apiCall(
          API_CONFIG.ENDPOINTS.TOWNS_SIDEWALK_BY_TOWN(filters.municipio_id),
        );

        if (response.ok) {
          setVeredas(response.veredas || []);
        }
      } catch (error) {
        //console.error("Error al cargar veredas:", error);
      } finally {
        setLoadingVeredas(false);
      }
    };

    fetchVeredas();
  }, [filters.municipio_id]);

  const handleToggleVereda = (veredaId: number) => {
    setFilters((prev) => {
      const current = prev.vereda_ids || [];
      const updated = current.includes(veredaId)
        ? current.filter((id) => id !== veredaId)
        : [...current, veredaId];
      return { ...prev, vereda_ids: updated };
    });
  };

  const handleToggleRecurso = (recursoId: number) => {
    setFilters((prev) => {
      const current = prev.recurso_ids || [];
      const updated = current.includes(recursoId)
        ? current.filter((id) => id !== recursoId)
        : [...current, recursoId];
      return { ...prev, recurso_ids: updated };
    });
  };

  const handleClearFilters = () => {
    setFilters({ valor_exacto: false });
    setVeredas([]);
  };

  const handleClose = () => {
    onClose(!isOpen);
  };

  const handleApply = () => {
    // Crear objeto limpio sin campos vacíos
    const cleanFilters: Partial<FilterData> = {};

    if (filters.motivo_afectacion)
      cleanFilters.motivo_afectacion = filters.motivo_afectacion;
    if (filters.direccion) cleanFilters.direccion = filters.direccion;
    if (filters.municipio_id) cleanFilters.municipio_id = filters.municipio_id;
    if (filters.vereda_ids && filters.vereda_ids.length > 0)
      cleanFilters.vereda_ids = filters.vereda_ids;
    if (filters.recurso_ids && filters.recurso_ids.length > 0)
      cleanFilters.recurso_ids = filters.recurso_ids;
    cleanFilters.valor_exacto = filters.valor_exacto;

    onApplyFilters(cleanFilters as FilterData);
    onClose(!isOpen);
  };

  const toggleSection = (section: string) => {
    setActiveSection(activeSection === section ? null : section);
  };

  if (!isOpen) return null;

  const activeFiltersCount = Object.entries(filters).filter(([key, value]) => {
    if (key === "valor_exacto") return false;
    if (value === undefined || value === "" || value === null) return false;
    if (Array.isArray(value) && value.length === 0) return false;
    return true;
  }).length;

  return createPortal(
    <div
      data-theme={theme}
      data-modal="advanced-filters"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
    >
      <div className="bg-base-100 rounded-2xl w-full max-w-3xl mx-4 shadow-2xl border border-base-300 max-h-[90vh] flex flex-col animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-5 border-b border-base-300 flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-success/10 rounded-xl flex items-center justify-center">
                <svg
                  className="w-5 h-5 text-success"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
              </div>
              <div>
                <h3 className="font-bold text-lg text-base-content">
                  Búsqueda Avanzada
                </h3>
                <p className="text-xs text-base-content/60">
                  {activeFiltersCount > 0
                    ? `${activeFiltersCount} filtro${
                        activeFiltersCount > 1 ? "s" : ""
                      } activo${activeFiltersCount > 1 ? "s" : ""}`
                    : "Consulta en base de datos"}
                </p>
              </div>
            </div>
            <button
              onClick={handleClose}
              className="btn btn-ghost btn-sm btn-circle"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Body - Scrollable */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {/* Información del Expediente */}
          <div className="space-y-3">
            <button
              onClick={() => toggleSection("basic")}
              className="w-full flex items-center justify-between p-3 bg-base-200 hover:bg-base-300 rounded-lg transition-colors"
            >
              <div className="flex items-center gap-2">
                <svg
                  className="w-5 h-5 text-success"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <span className="font-semibold">
                  Información del Expediente
                </span>
              </div>
              <svg
                className={`w-5 h-5 transition-transform ${
                  activeSection === "basic" ? "rotate-180" : ""
                }`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>

            {activeSection === "basic" && (
              <div className="space-y-3 pl-4">
                <div>
                  <label className="label">
                    <span className="label-text font-medium">
                      Motivo de Afectación
                    </span>
                  </label>
                  <input
                    type="text"
                    className="input input-bordered w-full"
                    placeholder="Buscar por motivo"
                    value={filters.motivo_afectacion || ""}
                    onChange={(e) =>
                      setFilters((prev) => ({
                        ...prev,
                        motivo_afectacion: e.target.value,
                      }))
                    }
                  />
                </div>

                <div>
                  <label className="label">
                    <span className="label-text font-medium">Dirección</span>
                  </label>
                  <input
                    type="text"
                    className="input input-bordered w-full"
                    placeholder="Buscar por dirección"
                    value={filters.direccion || ""}
                    onChange={(e) =>
                      setFilters((prev) => ({
                        ...prev,
                        direccion: e.target.value,
                      }))
                    }
                  />
                </div>
              </div>
            )}
          </div>

          {/* Filtros de Ubicación */}
          <div className="space-y-3">
            <button
              onClick={() => toggleSection("location")}
              className="w-full flex items-center justify-between p-3 bg-base-200 hover:bg-base-300 rounded-lg transition-colors"
            >
              <div className="flex items-center gap-2">
                <svg
                  className="w-5 h-5 text-success"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                </svg>
                <span className="font-semibold">Ubicación</span>
              </div>
              <svg
                className={`w-5 h-5 transition-transform ${
                  activeSection === "location" ? "rotate-180" : ""
                }`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>

            {activeSection === "location" && (
              <div className="space-y-3 pl-4">
                <div>
                  <label className="label">
                    <span className="label-text font-medium">Municipio</span>
                  </label>
                  <select
                    className="select select-bordered w-full"
                    value={filters.municipio_id || ""}
                    onChange={(e) => {
                      const value = e.target.value;
                      if (value) {
                        setFilters((prev) => ({
                          ...prev,
                          municipio_id: Number(value),
                          vereda_ids: [],
                        }));
                      } else {
                        setFilters((prev) => {
                          const newFilters = { ...prev };
                          delete newFilters.municipio_id;
                          delete newFilters.vereda_ids;
                          return newFilters;
                        });
                      }
                    }}
                  >
                    <option value="">Todos los municipios</option>
                    {municipioList.map((municipio) => (
                      <option key={municipio.id} value={municipio.id}>
                        {municipio.nombre}
                      </option>
                    ))}
                  </select>
                </div>

                {filters.municipio_id && (
                  <div>
                    <label className="label">
                      <span className="label-text font-medium">
                        Veredas
                        {loadingVeredas && (
                          <span className="loading loading-spinner loading-xs ml-2"></span>
                        )}
                      </span>
                    </label>
                    <div className="border border-base-300 rounded-lg p-3 max-h-40 overflow-y-auto bg-base-50">
                      {loadingVeredas ? (
                        <div className="flex items-center justify-center py-4">
                          <span className="loading loading-spinner loading-sm"></span>
                        </div>
                      ) : veredas.length === 0 ? (
                        <p className="text-sm text-base-content/60 text-center py-2">
                          No hay veredas disponibles
                        </p>
                      ) : (
                        <div className="space-y-2">
                          {veredas.map((vereda) => (
                            <label
                              key={vereda.id}
                              className="flex items-center gap-2 cursor-pointer hover:bg-base-200 p-2 rounded"
                            >
                              <input
                                type="checkbox"
                                className="checkbox checkbox-success checkbox-sm"
                                checked={
                                  filters.vereda_ids?.includes(vereda.id) ||
                                  false
                                }
                                onChange={() => handleToggleVereda(vereda.id)}
                              />
                              <span className="text-sm">{vereda.nombre}</span>
                            </label>
                          ))}
                        </div>
                      )}
                    </div>
                    {filters.vereda_ids && filters.vereda_ids.length > 0 && (
                      <p className="text-xs text-success mt-1">
                        {filters.vereda_ids.length} vereda
                        {filters.vereda_ids.length > 1 ? "s" : ""} seleccionada
                        {filters.vereda_ids.length > 1 ? "s" : ""}
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Recursos Afectados */}
          <div className="space-y-3">
            <button
              onClick={() => toggleSection("resources")}
              className="w-full flex items-center justify-between p-3 bg-base-200 hover:bg-base-300 rounded-lg transition-colors"
            >
              <div className="flex items-center gap-2">
                <svg
                  className="w-5 h-5 text-success"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <span className="font-semibold">Recursos Afectados</span>
              </div>
              <svg
                className={`w-5 h-5 transition-transform ${
                  activeSection === "resources" ? "rotate-180" : ""
                }`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>

            {activeSection === "resources" && (
              <div className="pl-4">
                <div className="border border-base-300 rounded-lg p-3 max-h-40 overflow-y-auto bg-base-50">
                  <div className="space-y-2">
                    {recursoAfectadoList.map((recurso) => (
                      <label
                        key={recurso.id}
                        className="flex items-center gap-2 cursor-pointer hover:bg-base-200 p-2 rounded"
                      >
                        <input
                          type="checkbox"
                          className="checkbox checkbox-success checkbox-sm"
                          checked={
                            filters.recurso_ids?.includes(recurso.id) || false
                          }
                          onChange={() => handleToggleRecurso(recurso.id)}
                        />
                        <span className="text-sm">{recurso.nombre}</span>
                      </label>
                    ))}
                  </div>
                </div>
                {filters.recurso_ids && filters.recurso_ids.length > 0 && (
                  <p className="text-xs text-success mt-1">
                    {filters.recurso_ids.length} recurso
                    {filters.recurso_ids.length > 1 ? "s" : ""} seleccionado
                    {filters.recurso_ids.length > 1 ? "s" : ""}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Modo de búsqueda */}
          <div className="bg-info/5 border border-info/20 rounded-lg p-4">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                className="checkbox checkbox-success"
                checked={filters.valor_exacto}
                onChange={(e) =>
                  setFilters((prev) => ({
                    ...prev,
                    valor_exacto: e.target.checked,
                  }))
                }
              />
              <div>
                <span className="font-medium text-base-content">
                  Búsqueda exacta
                </span>
                <p className="text-xs text-base-content/60 mt-0.5">
                  Buscar coincidencias exactas en lugar de parciales
                </p>
              </div>
            </label>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-base-300 flex justify-between gap-3 flex-shrink-0">
          <button
            onClick={handleClearFilters}
            className="btn btn-ghost gap-2"
            disabled={activeFiltersCount === 0}
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
            Limpiar
          </button>
          <div className="flex gap-2">
            <button onClick={handleClose} className="btn btn-ghost">
              Cancelar
            </button>
            <button
              onClick={handleApply}
              className="btn btn-success text-white gap-2"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              Buscar en BD
              {activeFiltersCount > 0 && (
                <span className="badge badge-sm bg-white text-success">
                  {activeFiltersCount}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}
