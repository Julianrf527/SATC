import { useMemo, useState } from "react";
import { apiCall } from "../../../utils/api";
import TableFileLog from "../../app-sancionatorio/Table/TableFileLog";
import CustomDateInput from "../Form/CustomDateInput";

type LogAuditoria = {
  id: number;
  usuario_id: number;
  usuario_nombre: string;
  usuario_documento?: string | null;
  usuario_correo: string;
  tabla_afectada: string;
  tipo_operacion: string;
  descripcion: string;
  expediente_radicado: string | null;
  id_registro: string | null;
  fecha: string;
  datos_anteriores: Record<string, unknown>;
  datos_nuevos: Record<string, unknown>;
};

type SearchFilters = {
  cedula: string;
  nombreUsuario: string;
  radicado: string;
  fechaInicio: string;
  fechaFin: string;
};

type Props = {
  title: string;
  body?: string;
  endpoint: string;
  moduleName?: string;
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
};


export default function GestionLogsManager({ title, body: _body, endpoint, moduleName, setToast }: Props) {
  const auditScope: "sanctioning" | "infraction" | "involved" = endpoint.includes("/infraction/")
    ? "infraction"
    : endpoint.includes("/involved/")
    ? "involved"
    : "sanctioning";
  const showRadicado = auditScope !== "involved";

  const [logs, setLogs] = useState<LogAuditoria[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalRecords, setTotalRecords] = useState(0);
  const [recordsPerPage] = useState(50);

  const [searchCedula, setSearchCedula] = useState("");
  const [searchNombreUsuario, setSearchNombreUsuario] = useState("");
  const [searchRadicado, setSearchRadicado] = useState("");
  const [searchFechaInicio, setSearchFechaInicio] = useState("");
  const [searchFechaFin, setSearchFechaFin] = useState("");

  const [usuarioFilter, setUsuarioFilter] = useState("");
  const [tablaFilter, setTablaFilter] = useState("all");
  const [operacionFilter, setOperacionFilter] = useState("all");
  const [radicadoFilter, setRadicadoFilter] = useState("");
  const [fechaFilter, setFechaFilter] = useState("");

  const searchValues = useMemo<SearchFilters>(() => ({
    cedula: searchCedula,
    nombreUsuario: searchNombreUsuario,
    radicado: searchRadicado,
    fechaInicio: searchFechaInicio,
    fechaFin: searchFechaFin,
  }), [searchCedula, searchNombreUsuario, searchRadicado, searchFechaInicio, searchFechaFin]);

  const fetchLogs = async (pageNumber: number, filters: SearchFilters, showToast = true) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.cedula.trim()) {
        const cedulaParam = auditScope === "involved" ? "documento_usuario" : "cedula";
        params.append(cedulaParam, filters.cedula.trim());
      }
      if (filters.nombreUsuario.trim()) params.append("nombre_usuario", filters.nombreUsuario.trim());
      if (filters.radicado.trim()) params.append("expediente_radicado", filters.radicado.trim());
      if (filters.fechaInicio) params.append("fecha_inicio", filters.fechaInicio);
      if (filters.fechaFin) params.append("fecha_fin", filters.fechaFin);

      const page = Number(pageNumber) || 1;
      params.append("limit", recordsPerPage.toString());
      params.append("offset", ((page - 1) * recordsPerPage).toString());

      const res = await apiCall(`${endpoint}?${params.toString()}`, { method: "GET" });

      if (res.ok) {
        setLogs(res.data || []);
        setTotalRecords(res.pagination?.total || res.total || 0);
        setCurrentPage(page);
        if (showToast)
          setToast({
            id: Date.now(),
            message: res.msg || `${res.pagination?.total || res.data?.length || 0} registros encontrados`,
            type: res.data?.length ? "success" : "error",
          });
      } else {
        setLogs([]); setTotalRecords(0); setCurrentPage(page);
        if (showToast)
          setToast({ id: Date.now(), message: res.msg || "Error al cargar los logs", type: "error" });
      }
    } catch {
      setLogs([]); setTotalRecords(0); setCurrentPage(pageNumber);
      if (showToast)
        setToast({ id: Date.now(), message: "Error al cargar los logs", type: "error" });
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    if (!searchCedula && !searchNombreUsuario && !searchRadicado && !searchFechaInicio && !searchFechaFin) {
      setToast({ id: Date.now(), message: "Ingrese al menos un criterio de búsqueda", type: "error" });
      return;
    }
    void fetchLogs(1, searchValues, true);
  };

  const handleClear = () => {
    setSearchCedula(""); setSearchNombreUsuario(""); setSearchRadicado("");
    setSearchFechaInicio(""); setSearchFechaFin("");
    setUsuarioFilter(""); setTablaFilter("all"); setOperacionFilter("all");
    setRadicadoFilter(""); setFechaFilter("");
    setLogs([]); setTotalRecords(0); setCurrentPage(1);
  };

  const hasActiveSearch = !!(searchCedula || searchNombreUsuario || searchRadicado || searchFechaInicio || searchFechaFin);
  const hasActiveFilter = !!(tablaFilter !== "all" || operacionFilter !== "all" || usuarioFilter || radicadoFilter || fechaFilter);

  const filteredLogs = useMemo(() => {
    const usuario = usuarioFilter.trim().toLowerCase();
    const radicado = radicadoFilter.trim().toLowerCase();
    const fecha = fechaFilter.trim();
    return logs.filter((log) => {
      const mU = usuario ? log.usuario_nombre?.toLowerCase().includes(usuario) ||
        log.usuario_correo?.toLowerCase().includes(usuario) ||
        log.usuario_documento?.toLowerCase().includes(usuario) ||
        String(log.usuario_id).includes(usuario) : true;
      const mT = tablaFilter === "all" ? true : log.tabla_afectada?.toLowerCase() === tablaFilter.toLowerCase();
      const mO = operacionFilter === "all" ? true : log.tipo_operacion === operacionFilter;
      const mR = radicado ? log.expediente_radicado?.toLowerCase().includes(radicado) : true;
      const mF = fecha ? log.fecha?.startsWith(fecha) : true;
      return mU && mT && mO && mR && mF;
    });
  }, [logs, usuarioFilter, tablaFilter, operacionFilter, radicadoFilter, fechaFilter]);

  const uniqueTables = useMemo(() =>
    Array.from(new Set(logs.map((l) => l.tabla_afectada).filter(Boolean))).sort(), [logs]);

  const uniqueUsuarios = useMemo(() => new Set(logs.map((l) => l.usuario_id)).size, [logs]);
  const uniqueRadicados = useMemo(() =>
    new Set(logs.map((l) => l.expediente_radicado).filter(Boolean)).size, [logs]);

  return (
    <>
      {/* Header estilo SignUpLayout */}
      <div className="bg-gradient-to-r from-base-100 to-base-200/50 border-b border-base-300 shadow-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div>
                <p className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wider">
                  {moduleName || "Auditoría"}
                </p>
                <h1 className="text-lg font-bold text-base-content">{title}</h1>
              </div>
            </div>

            {!loading && (
              <div className="flex items-center gap-3">
                <div className="text-right hidden sm:block">
                  <p className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wider">Total registros</p>
                  <p className="text-lg font-bold text-primary leading-tight">
                    {totalRecords}
                    <span className="text-xs font-normal text-base-content/50 ml-1">{filteredLogs.length} visibles</span>
                  </p>
                </div>
                <div className="hidden sm:flex items-center gap-2 pl-3 border-l border-base-300">
                  <div className="text-center">
                    <p className="text-lg font-bold text-info leading-tight">{uniqueUsuarios}</p>
                    <p className="text-[9px] text-base-content/50 uppercase">Usuarios</p>
                  </div>
                  {showRadicado && (
                    <div className="text-center">
                      <p className="text-lg font-bold text-success leading-tight">{uniqueRadicados}</p>
                      <p className="text-[9px] text-base-content/50 uppercase">Radicados</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="w-full min-h-[calc(100vh-5rem)] bg-gradient-to-br from-base-200 to-base-300 p-4">
        <div className="max-w-7xl mx-auto space-y-4">

          {/* Filtros */}
          <div className="card bg-base-100 shadow border border-base-300">
            <div className="card-body p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-semibold text-base-content/70 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L13 13.414V19a1 1 0 01-.553.894l-4 2A1 1 0 017 21v-7.586L3.293 6.707A1 1 0 013 6V4z" />
                  </svg>
                  Filtros de búsqueda
                  {(hasActiveSearch || hasActiveFilter) && (
                    <span className="badge badge-primary badge-sm">activos</span>
                  )}
                </span>
                <button onClick={handleClear} disabled={!hasActiveSearch && !hasActiveFilter}
                  className="btn btn-xs btn-ghost gap-1">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  Limpiar
                </button>
              </div>

              <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 ${showRadicado ? "xl:grid-cols-5" : "xl:grid-cols-4"}`}>
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-base-content/60">Cédula</span>
                  <input type="text" placeholder="Buscar por cédula..." className="input input-sm input-bordered"
                    value={searchCedula} onChange={(e) => setSearchCedula(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSearch()} />
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-base-content/60">Nombre del usuario</span>
                  <input type="text" placeholder="Buscar..." className="input input-sm input-bordered"
                    value={searchNombreUsuario} onChange={(e) => setSearchNombreUsuario(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSearch()} />
                </div>
                {showRadicado && (
                  <div className="flex flex-col gap-1">
                    <span className="text-xs font-medium text-base-content/60">Radicado</span>
                    <input type="text" placeholder="Buscar..." className="input input-sm input-bordered"
                      value={searchRadicado} onChange={(e) => setSearchRadicado(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleSearch()} />
                  </div>
                )}
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-base-content/60">Fecha desde</span>
                  <CustomDateInput className="input-sm"
                    value={searchFechaInicio} onChange={setSearchFechaInicio} />
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-base-content/60">Fecha hasta</span>
                  <div className="flex gap-2">
                    <CustomDateInput className="input-sm flex-1"
                      value={searchFechaFin} onChange={setSearchFechaFin} />
                    <button className="btn btn-sm btn-success text-white self-end" onClick={handleSearch} disabled={loading}>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                      Buscar
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Tabla */}
          <div className="card bg-base-100 shadow border border-base-300">
            <div className="card-body p-0">
              {loading ? (
                <div className="flex items-center justify-center py-16">
                  <span className="loading loading-spinner loading-lg text-primary" />
                  <p className="ml-4 text-base-content/60">Cargando logs...</p>
                </div>
              ) : (
                <TableFileLog
                  titles={showRadicado
                    ? ["Usuario", "Tabla", "Operacion", "Descripcion", "Radicado", "Fecha", "Acciones"]
                    : ["Usuario", "Tabla", "Operacion", "Descripcion", "Fecha", "Acciones"]
                  }
                  data={filteredLogs}
                  uniqueTables={uniqueTables}
                  usuarioFilter={usuarioFilter}
                  tablaFilter={tablaFilter}
                  operacionFilter={operacionFilter}
                  radicadoFilter={radicadoFilter}
                  fechaFilter={fechaFilter}
                  onUsuarioFilterChange={setUsuarioFilter}
                  onTablaFilterChange={setTablaFilter}
                  onOperacionFilterChange={setOperacionFilter}
                  onRadicadoFilterChange={setRadicadoFilter}
                  onFechaFilterChange={setFechaFilter}
                  auditScope={auditScope}
                  currentPage={currentPage}
                  totalRecords={totalRecords}
                  recordsPerPage={recordsPerPage}
                  onPageChange={(page) => fetchLogs(page, searchValues, false)}
                  isServerPagination={true}
                />
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
