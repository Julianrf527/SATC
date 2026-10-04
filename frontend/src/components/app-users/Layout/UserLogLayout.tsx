import { useState, useMemo } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import TableAudit from "../../app-users/Table/TableUserLog";
import CustomDateInput from "../../Common/Form/CustomDateInput";

type Auditoria = {
  id: number;
  usuario_id: number;
  usuario_nombre: string;
  usuario_documento?: string | null;
  usuario_correo: string;
  tabla_afectada: string;
  tipo_operacion: string;
  descripcion: string;
  id_registro: string | null;
  fecha: string;
  datos_anteriores: Record<string, unknown>;
  datos_nuevos: Record<string, unknown>;
};

type Props = {
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
};

export default function AuditLayout({ setToast }: Props) {
  const [audits, setAudits] = useState<Auditoria[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalRecords, setTotalRecords] = useState(0);
  const [recordsPerPage] = useState(50);

  const [searchCedula, setSearchCedula] = useState("");
  const [searchNombreUsuario, setSearchNombreUsuario] = useState("");
  const [searchFechaInicio, setSearchFechaInicio] = useState("");
  const [searchFechaFin, setSearchFechaFin] = useState("");

  const [usuarioFilter, setUsuarioFilter] = useState("");
  const [tablaFilter, setTablaFilter] = useState("all");
  const [operacionFilter, setOperacionFilter] = useState("all");
  const [fechaFilter, setFechaFilter] = useState("");

  const hasActiveSearch = !!(searchCedula || searchNombreUsuario || searchFechaInicio || searchFechaFin);

  const handleSearch = async (page: number = 1, showToast = true) => {
    if (!searchCedula && !searchNombreUsuario && !searchFechaInicio && !searchFechaFin) {
      setToast({ id: Date.now(), message: "Ingrese al menos un criterio de búsqueda", type: "error" });
      return;
    }
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchCedula) params.append("cedula", searchCedula);
      if (searchNombreUsuario) params.append("nombre_usuario", searchNombreUsuario);
      if (searchFechaInicio) params.append("fecha_inicio", searchFechaInicio);
      if (searchFechaFin) params.append("fecha_fin", searchFechaFin);
      const pageNum = Number(page) || 1;
      params.append("limit", recordsPerPage.toString());
      params.append("offset", ((pageNum - 1) * recordsPerPage).toString());

      const res = await apiCall(`${API_CONFIG.ENDPOINTS.USER_LOG}?${params.toString()}`, { method: "GET" });

      if (!res.ok) {
        setToast({ id: Date.now(), message: res.msg || "Error al cargar registros", type: "error" });
        setAudits([]); setTotalRecords(0);
      } else {
        setAudits(res.data || []);
        setTotalRecords(res.pagination?.total || res.total || 0);
        setCurrentPage(pageNum);
        if (showToast)
          setToast({ id: Date.now(), message: res.msg || `${res.pagination?.total || res.data?.length || 0} registros`, type: res.data?.length ? "success" : "error" });
      }
    } catch {
      setToast({ id: Date.now(), message: "Error al cargar registros de auditoría", type: "error" });
      setAudits([]); setTotalRecords(0);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setSearchCedula(""); setSearchNombreUsuario("");
    setSearchFechaInicio(""); setSearchFechaFin("");
    setAudits([]); setTotalRecords(0); setCurrentPage(1);
    setUsuarioFilter(""); setTablaFilter("all"); setOperacionFilter("all");
    setFechaFilter("");
  };

  const filteredAudits = useMemo(() => {
    const usuario = usuarioFilter.trim().toLowerCase();
    const fecha = fechaFilter.trim();
    return audits.filter((a) => {
      const mU = usuario ? a.usuario_nombre?.toLowerCase().includes(usuario) || a.usuario_correo?.toLowerCase().includes(usuario) || String(a.usuario_id).includes(usuario) : true;
      const mT = tablaFilter === "all" ? true : a.tabla_afectada?.toLowerCase() === tablaFilter.toLowerCase();
      const mO = operacionFilter === "all" ? true : a.tipo_operacion === operacionFilter;
      const mF = fecha ? a.fecha?.startsWith(fecha) : true;
      return mU && mT && mO && mF;
    });
  }, [audits, usuarioFilter, tablaFilter, operacionFilter, fechaFilter]);

  const uniqueTables = useMemo(() =>
    Array.from(new Set(audits.map((a) => a.tabla_afectada).filter(Boolean))).sort(), [audits]);

  return (
    <>
      {/* Header */}
      <div className="bg-gradient-to-r from-base-100 to-base-200/50 border-b border-base-300 shadow-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-info/10 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-info" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <div>
                <p className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wider">Módulo de Usuarios</p>
                <h1 className="text-lg font-bold text-base-content">Auditoría General</h1>
              </div>
            </div>
            <div className="hidden sm:flex items-center gap-2">
              <svg className="w-4 h-4 text-info/70 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-xs text-info/70 max-w-[220px]">
                Busca por cédula, nombre, tabla o ID de registro para consultar eventos del sistema.
              </p>
            </div>
            {!loading && audits.length > 0 && (
              <div className="text-right">
                <p className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wider">Resultados</p>
                <p className="text-lg font-bold text-info leading-tight">
                  {totalRecords}
                  <span className="text-xs font-normal text-base-content/50 ml-1">{filteredAudits.length} visibles</span>
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="w-full min-h-[calc(100vh-5rem)] bg-gradient-to-br from-base-200 to-base-300 p-4">
        <div className="max-w-7xl mx-auto space-y-4">

          {/* Filtros de búsqueda */}
          <div className="card bg-base-100 shadow border border-base-300">
            <div className="card-body p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-semibold text-base-content/70 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  Buscar registros
                  {hasActiveSearch && <span className="badge badge-info badge-sm">activos</span>}
                </span>
                <button onClick={handleClear} disabled={!hasActiveSearch && audits.length === 0}
                  className="btn btn-xs btn-ghost gap-1">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  Limpiar
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-3">
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-base-content/60">Cédula</span>
                  <input type="text" className="input input-sm input-bordered w-full"
                    placeholder="Buscar por cédula..."
                    value={searchCedula} onChange={(e) => setSearchCedula(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSearch()} disabled={loading} />
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-base-content/60">Nombre del usuario</span>
                  <input type="text" className="input input-sm input-bordered w-full"
                    placeholder="Ej: Juan Pérez"
                    value={searchNombreUsuario} onChange={(e) => setSearchNombreUsuario(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSearch()} disabled={loading} />
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-base-content/60">Fecha desde</span>
                  <CustomDateInput className="input-sm"
                    value={searchFechaInicio} onChange={setSearchFechaInicio} disabled={loading} />
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-base-content/60">Fecha hasta</span>
                  <CustomDateInput className="input-sm"
                    value={searchFechaFin} onChange={setSearchFechaFin} disabled={loading} />
                </div>
                <div className="flex items-end">
                  <button className="btn btn-sm btn-success text-white gap-2 w-full"
                    onClick={() => handleSearch(1, true)} disabled={loading}>
                    {loading
                      ? <><span className="loading loading-spinner loading-xs" />Buscando...</>
                      : <><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>Buscar</>}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Tabla */}
          <div className="card bg-base-100 shadow border border-base-300">
            <div className="card-body p-0">
              {loading ? (
                <div className="flex justify-center items-center py-16">
                  <span className="loading loading-spinner loading-lg text-info" />
                  <p className="ml-4 text-base-content/60">Buscando registros...</p>
                </div>
              ) : (
                <TableAudit
                  titles={["Usuario", "Evento", "Operación", "Descripción", "Fecha", "Acciones"]}
                  data={filteredAudits}
                  uniqueTables={uniqueTables}
                  usuarioFilter={usuarioFilter}
                  tablaFilter={tablaFilter}
                  operacionFilter={operacionFilter}
                  fechaFilter={fechaFilter}
                  onUsuarioFilterChange={setUsuarioFilter}
                  onTablaFilterChange={setTablaFilter}
                  onOperacionFilterChange={setOperacionFilter}
                  onFechaFilterChange={setFechaFilter}
                  currentPage={currentPage}
                  totalRecords={totalRecords}
                  recordsPerPage={recordsPerPage}
                  onPageChange={(page) => handleSearch(page, false)}
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
