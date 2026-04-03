import { useState, useMemo, useEffect } from "react";
import { useAuth } from "../../../context/AuthContext";
import ExpedienteCard from "./ExpedienteCard";
import NuevoExpediente from "./NuevoExpediente";
import AdvancedFiltersModal, { type FilterData } from "./AvancedFilterModal";
import type { Expediente, Quejoso } from "../../../types/infraccionApp";
import type { Municipio, ModeloGenerico } from "../../../types/common";
import { API_CONFIG, apiCall } from "../../../utils/api";

type Props = {
  municipioList: Municipio[];
  recursoAfectadoList: ModeloGenerico[];
  causaList: ModeloGenerico[];
  quejosoList: Quejoso[];
  setQuejosoList: (quejosos: Quejoso[]) => void;
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  setExpedienteSeleccionado: (expediente: Expediente | null) => void;
  expedienteList: Expediente[];
  setExpedienteList: (expedientes: Expediente[]) => void;
  isEditable?: boolean;
};

export default function ExpedienteList({
  municipioList,
  recursoAfectadoList,
  causaList,
  quejosoList,
  setQuejosoList,
  setToast,
  setExpedienteSeleccionado,
  expedienteList,
  setExpedienteList,
  isEditable = true,
}: Props) {
  const { user } = useAuth();

  // Filtros locales (búsqueda rápida)
  const [radicadoFilter, setRadicadoFilter] = useState("");
  const [nameFilter, setNameFilter] = useState("");
  const [fromDateFilter, setFromDateFilter] = useState("");
  const [untilDateFilter, setUntilDateFilter] = useState("");
  const [townFilter, setTownFilter] = useState("all");
  const [stageFilter, setStageFilter] = useState("all");
  const [archivedFilter, setArchivedFilter] = useState("all");
  const [showQuickFilters, setShowQuickFilters] = useState(false);

  // Estados para filtros avanzados
  const [showAdvancedModal, setShowAdvancedModal] = useState(false);
  const [advancedFilters, setAdvancedFilters] = useState<FilterData | null>(
    null,
  );
  const [isLoadingAdvanced, setIsLoadingAdvanced] = useState(false);
  const [avanzadaExpedienteList, setAvanzadoExpedienteList] = useState<
    Expediente[]
  >([]);

  const [isAdding, setIsAdding] = useState(false);
  const [noFiles, setNoFiles] = useState(false);

  useEffect(() => {
    if (expedienteList.length === 0) {
      setNoFiles(true);
    } else {
      setNoFiles(false);
    }
  }, [expedienteList]);

  const handleNewClick = () => setIsAdding(true);
  const handleCancel = () => setIsAdding(false);

  const agregarExpediente = (expediente: Expediente) => {
    setExpedienteList([expediente, ...expedienteList]);
    setNoFiles(false);
  };

  // Municipios únicos en expedientes cargados
  const availableTowns = useMemo(() => {
    const municipios = new Set<string>();
    const currentList = advancedFilters
      ? avanzadaExpedienteList
      : expedienteList;
    currentList.forEach((f) => {
      if (f.municipio.nombre) {
        municipios.add(f.municipio.nombre);
      }
    });
    return Array.from(municipios);
  }, [expedienteList, avanzadaExpedienteList, advancedFilters]);

  // Etapas únicas en expedientes cargados
  const availableStages = useMemo(() => {
    const etapas = new Set<string>();
    const currentList = advancedFilters
      ? avanzadaExpedienteList
      : expedienteList;
    currentList.forEach((f) => {
      if (f.etapa_actual) {
        etapas.add(f.etapa_actual);
      }
    });
    return Array.from(etapas).sort();
  }, [expedienteList, avanzadaExpedienteList, advancedFilters]);

  // Aplicar filtros avanzados (llamada al backend)
  const applyAdvancedFilters = async (filters: FilterData) => {
    setIsLoadingAdvanced(true);
    /* console.log("[FileList] Enviando filtros avanzados:", filters);
    console.log("[FileList] Filtros en JSON:", JSON.stringify(filters, null, 2)); */
    try {
      const response = await apiCall(API_CONFIG.ENDPOINTS.FILE_FILTER, {
        method: "POST",
        body: JSON.stringify(filters),
      });

      if (!response.ok) {
        throw new Error("Error al aplicar filtros");
      } else {
        setAvanzadoExpedienteList(response.data);
        setAdvancedFilters(filters);
        setToast({
          id: Date.now(),
          message: `Se encontraron ${response.data.length} expedientes`,
          type: "success",
        });
      }
    } catch (error) {
      /* console.error("Error al aplicar filtros avanzados:", error); */
      setToast({
        id: Date.now(),
        message: "Error al aplicar filtros avanzados",
        type: "error",
      });
    } finally {
      setIsLoadingAdvanced(false);
    }
  };

  // Limpiar filtros avanzados
  const clearAdvancedFilters = () => {
    setAdvancedFilters(null);
    setAvanzadoExpedienteList([]);
  };

  // Filtro de expedientes (LOCALES sobre la lista actual)
  const filteredFiles = useMemo(() => {
    const currentList = advancedFilters
      ? avanzadaExpedienteList
      : expedienteList;

    return currentList.filter((f) => {
      const matchesRadicado = radicadoFilter
        ? f.radicado.toLowerCase().includes(radicadoFilter.toLowerCase())
        : true;

      const matchesName = nameFilter
        ? isNaN(Number(nameFilter))
          ? f.involucrados.some((i) =>
              i.nombre.toLowerCase().includes(nameFilter.toLowerCase()),
            )
          : f.involucrados.some((i) =>
              i.numero_documento.toString().includes(nameFilter.toLowerCase()),
            )
        : true;

      const matchesFromDate = fromDateFilter
        ? f.fecha_creacion >= fromDateFilter
        : true;
      const matchesUntilDate = untilDateFilter
        ? f.fecha_creacion <= untilDateFilter
        : true;

      const matchesTown =
        townFilter === "all" ? true : f.municipio.nombre === townFilter;

      const matchesStage =
        stageFilter === "all" ? true : f.etapa_actual === stageFilter;

      const matchesArchived =
        archivedFilter === "all"
          ? true
          : archivedFilter === "archived"
            ? f.archivado === true
            : f.archivado === false;

      return (
        matchesRadicado &&
        matchesName &&
        matchesFromDate &&
        matchesUntilDate &&
        matchesTown &&
        matchesStage &&
        matchesArchived
      );
    });
  }, [
    expedienteList,
    avanzadaExpedienteList,
    advancedFilters,
    radicadoFilter,
    nameFilter,
    fromDateFilter,
    untilDateFilter,
    townFilter,
    stageFilter,
    archivedFilter,
  ]);

  const clearAllFilters = () => {
    setRadicadoFilter("");
    setNameFilter("");
    setFromDateFilter("");
    setUntilDateFilter("");
    setTownFilter("all");
    setStageFilter("all");
    setArchivedFilter("all");
    clearAdvancedFilters();
  };

  const hasActiveFilters =
    radicadoFilter ||
    nameFilter ||
    fromDateFilter ||
    untilDateFilter ||
    townFilter !== "all" ||
    stageFilter !== "all" ||
    archivedFilter !== "all" ||
    advancedFilters !== null;

  return (
    <>
      <div className="w-80 flex flex-col h-full bg-base-100">
        {/* HEADER */}
        {!isAdding && (
          <div className="flex-shrink-0 p-6 border-b border-base-300 bg-base-100">
            <h2 className="text-2xl font-bold text-base-content mb-4">
              Expedientes
            </h2>

            {/* Filtro principal - Radicado */}
            <div className="relative">
              <input
                className="w-full input input-bordered"
                placeholder="Buscar por radicado..."
                type="text"
                value={radicadoFilter}
                onChange={(e) => setRadicadoFilter(e.target.value)}
              />
              <svg
                className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-base-content/40"
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

            {/* Botones de filtros */}
            <div className="mt-3 flex gap-2">
              {/* Filtros rápidos */}
              <button
                onClick={() => setShowQuickFilters(!showQuickFilters)}
                className="btn btn-ghost btn-sm flex-1 justify-between"
              >
                <span className="flex items-center gap-2">
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
                      d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
                    />
                  </svg>
                  Rápidos
                </span>
                <svg
                  className={`w-4 h-4 transition-transform ${
                    showQuickFilters ? "rotate-180" : "rotate-0"
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

              {/* Filtros avanzados (BD) */}
              <button
                onClick={() => setShowAdvancedModal(true)}
                className={`btn btn-sm flex-1 gap-2 ${
                  advancedFilters ? "btn-success text-white" : "btn-outline"
                }`}
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
                Avanzados
                {advancedFilters && (
                  <span className="badge badge-sm bg-white text-success">
                    BD
                  </span>
                )}
              </button>
            </div>

            {/* Filtros rápidos colapsables */}
            <div
              className={`${
                showQuickFilters ? "block" : "hidden"
              } mt-4 space-y-3`}
            >
              <input
                className="input input-bordered input-sm w-full"
                placeholder="Nombre o documento"
                type="text"
                value={nameFilter}
                onChange={(e) => setNameFilter(e.target.value)}
              />

              <div className="grid grid-cols-2 gap-2">
                <input
                  type="date"
                  className="input input-bordered input-sm"
                  value={fromDateFilter}
                  onChange={(e) => setFromDateFilter(e.target.value)}
                  title="Fecha desde"
                />
                <input
                  type="date"
                  className="input input-bordered input-sm"
                  value={untilDateFilter}
                  onChange={(e) => setUntilDateFilter(e.target.value)}
                  title="Fecha hasta"
                />
              </div>

              <select
                className="select select-bordered select-sm w-full"
                value={townFilter}
                onChange={(e) => setTownFilter(e.target.value)}
              >
                <option value="all">Todos los municipios</option>
                {availableTowns.map((mun) => (
                  <option value={mun} key={mun}>
                    {mun}
                  </option>
                ))}
              </select>

              <select
                className="select select-bordered select-sm w-full"
                value={stageFilter}
                onChange={(e) => setStageFilter(e.target.value)}
              >
                <option value="all">Todas las etapas</option>
                {availableStages.map((etapa) => (
                  <option value={etapa} key={etapa}>
                    {etapa}
                  </option>
                ))}
              </select>

              <select
                className="select select-bordered select-sm w-full"
                value={archivedFilter}
                onChange={(e) => setArchivedFilter(e.target.value)}
              >
                <option value="all">Todos los estados</option>
                <option value="archived">Solo archivados</option>
                <option value="active">Solo activos</option>
              </select>
            </div>

            {/* Botón limpiar filtros */}
            {hasActiveFilters && (
              <button
                onClick={clearAllFilters}
                className="btn btn-sm btn-ghost w-full mt-3 gap-2"
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
                Limpiar todos los filtros
              </button>
            )}
          </div>
        )}

        {/* RESULTADOS Y ESTADÍSTICAS */}
        <div
          className={`${
            isAdding ? "hidden" : "block"
          } flex-shrink-0 px-6 py-3 bg-base-200 border-b border-base-300`}
        >
          <div className="flex items-center justify-between text-sm">
            <span className="text-base-content/70">
              {filteredFiles.length} de{" "}
              {advancedFilters
                ? avanzadaExpedienteList.length
                : expedienteList.length}{" "}
              expedientes
            </span>
            <div className="flex gap-2">
              {advancedFilters && (
                <span className="badge badge-success text-white badge-sm">
                  Búsqueda BD
                </span>
              )}
              {filteredFiles.length !==
                (advancedFilters
                  ? avanzadaExpedienteList.length
                  : expedienteList.length) && (
                <span className="badge badge-info text-white badge-sm">
                  Filtrado
                </span>
              )}
              {isLoadingAdvanced && (
                <span className="loading loading-spinner loading-sm"></span>
              )}
            </div>
          </div>
        </div>

        {/* LISTA SCROLLEABLE DE TARJETAS */}
        <div
          className={`${
            isAdding ? "hidden" : "block"
          } flex-1 overflow-y-auto p-4 space-y-3`}
        >
          {isLoadingAdvanced ? (
            <div className="flex flex-col items-center justify-center py-12">
              <span className="loading loading-spinner loading-lg text-success"></span>
              <p className="text-base-content/60 text-sm mt-4">
                Buscando en base de datos...
              </p>
            </div>
          ) : noFiles && !advancedFilters ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="w-16 h-16 bg-base-200 rounded-full flex items-center justify-center mb-4">
                <svg
                  className="w-8 h-8 text-base-content/40"
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
              </div>
              <h3 className="text-lg font-medium text-base-content/70 mb-2">
                Sin expedientes
              </h3>
              <p className="text-base-content/50 text-sm">
                {isEditable
                  ? "¡Comienza creando un nuevo expediente!"
                  : "No hay expedientes disponibles."}
              </p>
            </div>
          ) : filteredFiles.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="w-16 h-16 bg-base-200 rounded-full flex items-center justify-center mb-4">
                <svg
                  className="w-8 h-8 text-base-content/40"
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
              <h3 className="text-lg font-medium text-base-content/70 mb-2">
                Sin resultados
              </h3>
              <p className="text-base-content/50 text-sm">
                {advancedFilters
                  ? "No se encontraron expedientes con los criterios avanzados"
                  : "Intenta ajustar los filtros de búsqueda"}
              </p>
            </div>
          ) : (
            filteredFiles.map((expediente) => (
              <ExpedienteCard
                key={expediente.radicado}
                radicado={expediente.radicado}
                fecha_radicado={expediente.fecha_radicado}
                fecha_creacion={expediente.fecha_creacion}
                municipio={expediente.municipio.nombre || "Desconocido"}
                onClick={() => setExpedienteSeleccionado(expediente)}
              />
            ))
          )}
        </div>

        {/* BOTÓN NUEVO (FIJO) */}
        {isEditable && (
          <div
            className={`${
              isAdding ? "hidden" : "block"
            } flex-shrink-0 p-6 border-t border-base-300 bg-base-100`}
          >
            <button
              className="btn btn-success text-white w-full"
              onClick={handleNewClick}
            >
              + Nuevo Expediente
            </button>
          </div>
        )}

        {/* FORMULARIO NuevoExpediente */}
        {isEditable && (
          <div className={`${isAdding ? "block" : "hidden"} h-full`}>
            <NuevoExpediente
              userId={Number(user?.user_id)}
              municipioList={municipioList}
              recursoAfectadoList={recursoAfectadoList}
              quejosoList={quejosoList}
              setQuejosoList={setQuejosoList}
              causaList={causaList}
              setToast={setToast}
              onCancel={handleCancel}
              agregarExpediente={agregarExpediente}
            />
          </div>
        )}
      </div>

      {/* MODAL DE FILTROS AVANZADOS */}
      {showAdvancedModal && (
        <AdvancedFiltersModal
          isOpen={showAdvancedModal}
          onClose={() => setShowAdvancedModal(false)}
          onApplyFilters={applyAdvancedFilters}
          municipioList={municipioList}
          recursoAfectadoList={recursoAfectadoList}
        />
      )}
    </>
  );
}
