import { useState, useMemo } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import TitleForm from "../../Label/TitleForm";
import TableAudit from "../../app-users/Table/TableUserLog";

type Auditoria = {
  id: number;
  usuario_id: number;
  usuario_nombre: string;
  usuario_correo: string;
  tabla_afectada: string;
  tipo_operacion: string;
  descripcion: string;
  id_registro: string | null;
  fecha: string;
  datos_anteriores: any;
  datos_nuevos: any;
};

type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function AuditLayout({ setToast }: Props) {
  const [audits, setAudits] = useState<Auditoria[]>([]);
  const [loading, setLoading] = useState(false);

  // Paginación del servidor
  const [currentPage, setCurrentPage] = useState(1);
  const [totalRecords, setTotalRecords] = useState(0);
  const [recordsPerPage] = useState(50); // Registros por página

  // Campos de búsqueda
  const [searchUsuarioId, setSearchUsuarioId] = useState("");
  const [searchNombreUsuario, setSearchNombreUsuario] = useState("");
  const [searchTabla, setSearchTabla] = useState("");
  const [searchIdRegistro, setSearchIdRegistro] = useState("");
  const [searchFechaInicio, setSearchFechaInicio] = useState("");
  const [searchFechaFin, setSearchFechaFin] = useState("");

  // Estado para filtros avanzados
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);

  // Filtros internos
  const [usuarioFilter, setUsuarioFilter] = useState("");
  const [tablaFilter, setTablaFilter] = useState("all");
  const [operacionFilter, setOperacionFilter] = useState("all");
  const [idRegistroFilter, setIdRegistroFilter] = useState("");
  const [fechaFilter, setFechaFilter] = useState("");

  // Búsqueda de auditoría con paginación
  const handleSearch = async (page: number = 1, showToast: boolean = true) => {
    if (
      !searchUsuarioId &&
      !searchNombreUsuario &&
      !searchTabla &&
      !searchIdRegistro
    ) {
      setToast({
        id: Date.now(),
        message:
          "Ingrese al menos un criterio de búsqueda (Cedula, Nombre, Tabla o ID Registro)",
        type: "error",
      });
      return;
    }

    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchUsuarioId) params.append("usuario_id", searchUsuarioId);
      if (searchNombreUsuario)
        params.append("nombre_usuario", searchNombreUsuario);
      if (searchTabla) params.append("tabla_afectada", searchTabla);
      if (searchIdRegistro) params.append("id_registro", searchIdRegistro);
      if (searchFechaInicio) params.append("fecha_inicio", searchFechaInicio);
      if (searchFechaFin) params.append("fecha_fin", searchFechaFin);
      
      // Agregar parámetros de paginación
      const pageNumber = Number(page) || 1;
      const offset = (pageNumber - 1) * recordsPerPage;
      params.append("limit", recordsPerPage.toString());
      params.append("offset", offset.toString());

      const res = await apiCall(
        `${API_CONFIG.ENDPOINTS.USER_LOG}?${params.toString()}`,
        {
          method: "GET",
        }
      );

      if (!res.ok) {
        setToast({
          id: Date.now(),
          message: res.msg || "Error al cargar los registros de auditoría",
          type: "error",
        });
        setAudits([]);
        setTotalRecords(0);
      } else {
        setAudits(res.data || []);
        setTotalRecords(res.pagination?.total || res.total || 0);
        setCurrentPage(pageNumber);
        
        if (showToast) {
          if (res.data && res.data.length > 0) {
            setToast({
              id: Date.now(),
              message: res.msg || `Se encontraron ${res.pagination?.total || res.data.length} registros`,
              type: "success",
            });
          } else {
            setToast({
              id: Date.now(),
              message: "No se encontraron registros",
              type: "error",
            });
          }
        }
      }
    } catch (error) {
      setToast({
        id: Date.now(),
        message: "Error al cargar los registros de auditoría",
        type: "error",
      });
      setAudits([]);
      setTotalRecords(0);
    } finally {
      setLoading(false);
    }
  };

  // Limpiar búsqueda
  const handleClear = () => {
    setSearchUsuarioId("");
    setSearchNombreUsuario("");
    setSearchTabla("");
    setSearchIdRegistro("");
    setSearchFechaInicio("");
    setSearchFechaFin("");
    setAudits([]);
    setTotalRecords(0);
    setCurrentPage(1);
    setUsuarioFilter("");
    setTablaFilter("all");
    setOperacionFilter("all");
    setIdRegistroFilter("");
    setFechaFilter("");
  };

  // Filtrado instantáneo
  const filteredAudits = useMemo(() => {
    const usuario = usuarioFilter.trim().toLowerCase();
    const idRegistro = idRegistroFilter.trim().toLowerCase();
    const fecha = fechaFilter.trim();

    return audits.filter((audit) => {
      const matchesUsuario = usuario
        ? audit.usuario_nombre?.toLowerCase().includes(usuario) ||
          audit.usuario_correo?.toLowerCase().includes(usuario) ||
          String(audit.usuario_id).includes(usuario)
        : true;

      const matchesTabla =
        tablaFilter === "all"
          ? true
          : audit.tabla_afectada?.toLowerCase() === tablaFilter.toLowerCase();

      const matchesOperacion =
        operacionFilter === "all"
          ? true
          : audit.tipo_operacion === operacionFilter;

      const matchesIdRegistro = idRegistro
        ? audit.id_registro?.toLowerCase().includes(idRegistro)
        : true;

      const matchesFecha = fecha ? audit.fecha?.startsWith(fecha) : true;

      return (
        matchesUsuario &&
        matchesTabla &&
        matchesOperacion &&
        matchesIdRegistro &&
        matchesFecha
      );
    });
  }, [
    audits,
    usuarioFilter,
    tablaFilter,
    operacionFilter,
    idRegistroFilter,
    fechaFilter,
  ]);

  // Obtener valores únicos para filtros
  const uniqueTables = useMemo(() => {
    const tables = new Set(
      audits.map((audit) => audit.tabla_afectada).filter(Boolean)
    );
    return Array.from(tables).sort();
  }, [audits]);

  return (
    <div className="bg-base-200">
      <section className="w-full h-full flex justify-center items-start min-h-[calc(100vh-4rem)] overflow-hidden p-4">
        <div className="w-full max-w-7xl h-full">
          <div className="card bg-base-100 shadow-xl border border-base-300 w-full h-full">
            <div className="card-body px-6 py-6 flex flex-col h-full overflow-hidden">
              <TitleForm
                title="Auditoría General"
                body="Busca y filtra los registros de auditoría del sistema por usuario, tabla o registro."
              />

              {/* Formulario de búsqueda compacto */}
              <div className="bg-base-200 rounded-lg border border-base-300 mb-4">
                {/* Filtros básicos */}
                <div className="p-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
                    <div className="form-control">
                      <label className="label py-1">
                        <span className="label-text text-sm font-medium">Cedula</span>
                      </label>
                      <input
                        type="number"
                        className="input input-sm input-bordered w-full"
                        placeholder="Ej: 1233506795"
                        value={searchUsuarioId}
                        onChange={(e) => setSearchUsuarioId(e.target.value)}
                        disabled={loading}
                      />
                    </div>

                    <div className="form-control">
                      <label className="label py-1">
                        <span className="label-text text-sm font-medium">Nombre Usuario</span>
                      </label>
                      <input
                        type="text"
                        className="input input-sm input-bordered w-full"
                        placeholder="Ej: Juan Pérez"
                        value={searchNombreUsuario}
                        onChange={(e) => setSearchNombreUsuario(e.target.value)}
                        disabled={loading}
                      />
                    </div>

                    <div className="form-control">
                      <label className="label py-1">
                        <span className="label-text text-sm font-medium">Tabla</span>
                      </label>
                      <input
                        type="text"
                        className="input input-sm input-bordered w-full"
                        placeholder="Ej: expediente, usuario"
                        value={searchTabla}
                        onChange={(e) => setSearchTabla(e.target.value)}
                        disabled={loading}
                      />
                    </div>
                  </div>

                  {/* Filtros avanzados (colapsable) */}
                  {showAdvancedFilters && (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3 p-4 bg-base-300/30 rounded-lg border border-base-300">
                      <div className="form-control">
                        <label className="label py-1">
                          <span className="label-text text-sm font-medium">ID Registro</span>
                        </label>
                        <input
                          type="text"
                          className="input input-sm input-bordered w-full"
                          placeholder="Ej: 12345"
                          value={searchIdRegistro}
                          onChange={(e) => setSearchIdRegistro(e.target.value)}
                          disabled={loading}
                        />
                      </div>

                      <div className="form-control">
                        <label className="label py-1">
                          <span className="label-text text-sm font-medium">Fecha Inicio</span>
                        </label>
                        <input
                          type="date"
                          className="input input-sm input-bordered w-full"
                          value={searchFechaInicio}
                          onChange={(e) => setSearchFechaInicio(e.target.value)}
                          disabled={loading}
                        />
                      </div>

                      <div className="form-control">
                        <label className="label py-1">
                          <span className="label-text text-sm font-medium">Fecha Fin</span>
                        </label>
                        <input
                          type="date"
                          className="input input-sm input-bordered w-full"
                          value={searchFechaFin}
                          onChange={(e) => setSearchFechaFin(e.target.value)}
                          disabled={loading}
                        />
                      </div>
                    </div>
                  )}

                  {/* Toggle filtros avanzados y botones de acción en la misma fila */}
                  <div className="flex gap-2 justify-between items-center">
                    <button
                      type="button"
                      onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
                      className="btn btn-ghost btn-sm gap-2"
                    >
                      <svg
                        className={`w-4 h-4 transition-transform ${showAdvancedFilters ? 'rotate-180' : ''}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                      Filtros Avanzados
                      {(searchIdRegistro || searchFechaInicio || searchFechaFin) && (
                        <span className="badge badge-sm badge-success">Activos</span>
                      )}
                    </button>

                    <div className="flex gap-2">
                      <button
                        className="btn btn-sm btn-ghost gap-2"
                        onClick={handleClear}
                        disabled={loading}
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                        Limpiar
                      </button>
                      <button
                        className="btn btn-sm btn-success text-white gap-2"
                        onClick={() => handleSearch(1, true)}
                        disabled={loading}
                      >
                      {loading ? (
                        <>
                          <span className="loading loading-spinner loading-xs"></span>
                          Buscando...
                        </>
                      ) : (
                        <>
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                          </svg>
                          Buscar
                        </>
                      )}
                    </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Tabla de auditoría */}
              <TableAudit
                titles={[
                  "ID",
                  "Usuario",
                  "Tabla",
                  "Operación",
                  "Descripción",
                  "ID Registro",
                  "Fecha",
                  "Acciones",
                ]}
                data={filteredAudits}
                uniqueTables={uniqueTables}
                usuarioFilter={usuarioFilter}
                tablaFilter={tablaFilter}
                operacionFilter={operacionFilter}
                idRegistroFilter={idRegistroFilter}
                fechaFilter={fechaFilter}
                onUsuarioFilterChange={setUsuarioFilter}
                onTablaFilterChange={setTablaFilter}
                onOperacionFilterChange={setOperacionFilter}
                onIdRegistroFilterChange={setIdRegistroFilter}
                onFechaFilterChange={setFechaFilter}
                currentPage={currentPage}
                totalRecords={totalRecords}
                recordsPerPage={recordsPerPage}
                onPageChange={(page) => handleSearch(page, false)}
                isServerPagination={true}
              />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
