import { useState, useMemo } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import TitleForm from "../../Common/Label/TitleForm";
import TableFileLog from "../Table/TableFileLog";

type LogAuditoria = {
  id: number;
  usuario_id: number;
  usuario_nombre: string;
  usuario_correo: string;
  tabla_afectada: string;
  tipo_operacion: string;
  descripcion: string;
  expediente_radicado: string | null;
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

export default function FileLogLayout({ setToast }: Props) {
  const [logs, setLogs] = useState<LogAuditoria[]>([]);
  const [loading, setLoading] = useState(false);

  // Paginación del servidor
  const [currentPage, setCurrentPage] = useState(1);
  const [totalRecords, setTotalRecords] = useState(0);
  const [recordsPerPage] = useState(50); // Registros por página

  // Campos de búsqueda
  const [searchUsuarioId, setSearchUsuarioId] = useState("");
  const [searchRadicado, setSearchRadicado] = useState("");
  const [searchIdRegistro, setSearchIdRegistro] = useState("");
  const [searchFechaInicio, setSearchFechaInicio] = useState("");
  const [searchFechaFin, setSearchFechaFin] = useState("");

  // Filtros internos
  const [usuarioFilter, setUsuarioFilter] = useState("");
  const [tablaFilter, setTablaFilter] = useState("all");
  const [operacionFilter, setOperacionFilter] = useState("all");
  const [radicadoFilter, setRadicadoFilter] = useState("");
  const [fechaFilter, setFechaFilter] = useState("");

  // Búsqueda de logs con paginación
  const handleSearch = async (page: number = 1, showToast: boolean = true) => {
    if (!searchUsuarioId && !searchRadicado) {
      setToast({
        id: Date.now(),
        message:
          "Ingrese al menos un criterio de búsqueda (Usuario ID o Radicado)",
        type: "error",
      });
      return;
    }

    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchUsuarioId) params.append("usuario_id", searchUsuarioId);
      if (searchRadicado) params.append("expediente_radicado", searchRadicado);
      if (searchIdRegistro) params.append("id_registro", searchIdRegistro);
      if (searchFechaInicio) params.append("fecha_inicio", searchFechaInicio);
      if (searchFechaFin) params.append("fecha_fin", searchFechaFin);

      // Agregar parámetros de paginación
      const pageNumber = Number(page) || 1;
      const offset = (pageNumber - 1) * recordsPerPage;
      params.append("limit", recordsPerPage.toString());
      params.append("offset", offset.toString());

      const res = await apiCall(
        `${API_CONFIG.ENDPOINTS.AUDIT_LOGS}?${params.toString()}`,
        {
          method: "GET",
        },
      );

      if (!res.ok) {
        setToast({
          id: Date.now(),
          message: res.msg || "Error al cargar los logs",
          type: "error",
        });
        setLogs([]);
        setTotalRecords(0);
      } else {
        setLogs(res.data || []);
        setTotalRecords(res.pagination?.total || res.total || 0);
        setCurrentPage(pageNumber);

        if (showToast) {
          if (res.data && res.data.length > 0) {
            setToast({
              id: Date.now(),
              message:
                res.msg ||
                `Se encontraron ${res.pagination?.total || res.data.length} registros`,
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
        message: "Error al cargar los logs",
        type: "error",
      });
      setLogs([]);
      setTotalRecords(0);
    } finally {
      setLoading(false);
    }
  };

  // Limpiar búsqueda
  const handleClear = () => {
    setSearchUsuarioId("");
    setSearchRadicado("");
    setSearchIdRegistro("");
    setSearchFechaInicio("");
    setSearchFechaFin("");
    setLogs([]);
    setTotalRecords(0);
    setCurrentPage(1);
    setUsuarioFilter("");
    setTablaFilter("all");
    setOperacionFilter("all");
    setRadicadoFilter("");
    setFechaFilter("");
  };

  // Filtrado instantáneo
  const filteredLogs = useMemo(() => {
    const usuario = usuarioFilter.trim().toLowerCase();
    const radicado = radicadoFilter.trim().toLowerCase();
    const fecha = fechaFilter.trim();

    return logs.filter((log) => {
      const matchesUsuario = usuario
        ? log.usuario_nombre?.toLowerCase().includes(usuario) ||
          log.usuario_correo?.toLowerCase().includes(usuario) ||
          String(log.usuario_id).includes(usuario)
        : true;

      const matchesTabla =
        tablaFilter === "all"
          ? true
          : log.tabla_afectada?.toLowerCase() === tablaFilter.toLowerCase();

      const matchesOperacion =
        operacionFilter === "all"
          ? true
          : log.tipo_operacion === operacionFilter;

      const matchesRadicado = radicado
        ? log.expediente_radicado?.toLowerCase().includes(radicado)
        : true;

      const matchesFecha = fecha ? log.fecha?.startsWith(fecha) : true;

      return (
        matchesUsuario &&
        matchesTabla &&
        matchesOperacion &&
        matchesRadicado &&
        matchesFecha
      );
    });
  }, [
    logs,
    usuarioFilter,
    tablaFilter,
    operacionFilter,
    radicadoFilter,
    fechaFilter,
  ]);

  // Obtener valores únicos para filtros
  const uniqueTables = useMemo(() => {
    const tables = new Set(
      logs.map((log) => log.tabla_afectada).filter(Boolean),
    );
    return Array.from(tables).sort();
  }, [logs]);

  return (
    <div className="bg-base-200">
      <section className="w-full h-full flex justify-center items-start min-h-[calc(100vh-4rem)] overflow-hidden p-4">
        <div className="w-full max-w-7xl h-full">
          <div className="card bg-base-100 shadow-xl border border-base-300 w-full h-full">
            <div className="card-body px-6 py-6 flex flex-col h-full overflow-hidden">
              <TitleForm
                title="Logs de Auditoría"
                body="Busca y filtra los registros de auditoría del sistema."
              />

              {/* Formulario de búsqueda compacto */}
              <div className="bg-base-200 rounded-lg border border-base-300 mb-4">
                {/* Filtros básicos */}
                <div className="p-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
                    <div className="md:col-span-2">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <div className="form-control">
                          <label className="label py-1">
                            <span className="label-text text-sm font-medium">
                              Usuario ID
                            </span>
                          </label>
                          <input
                            type="number"
                            className="input input-sm input-bordered w-full"
                            placeholder="Ej: 1231574827"
                            value={searchUsuarioId}
                            onChange={(e) => setSearchUsuarioId(e.target.value)}
                            disabled={loading}
                          />
                        </div>

                        <div className="form-control">
                          <label className="label py-1">
                            <span className="label-text text-sm font-medium">
                              Radicado
                            </span>
                          </label>
                          <input
                            type="text"
                            className="input input-sm input-bordered w-full"
                            placeholder="Ej: 2024EE1001"
                            value={searchRadicado}
                            onChange={(e) => setSearchRadicado(e.target.value)}
                            disabled={loading}
                          />
                        </div>

                        <div className="form-control">
                          <label className="label py-1">
                            <span className="label-text text-sm font-medium">
                              ID Registro
                            </span>
                          </label>
                          <input
                            type="text"
                            className="input input-sm input-bordered w-full"
                            placeholder="Ej: 12345"
                            value={searchIdRegistro}
                            onChange={(e) =>
                              setSearchIdRegistro(e.target.value)
                            }
                            disabled={loading}
                          />
                        </div>
                      </div>
                    </div>

                    <div className="md:col-span-1">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div className="form-control">
                          <label className="label py-1">
                            <span className="label-text text-sm font-medium">
                              Fecha Inicio
                            </span>
                          </label>
                          <input
                            type="date"
                            className="input input-sm input-bordered w-full"
                            value={searchFechaInicio}
                            onChange={(e) =>
                              setSearchFechaInicio(e.target.value)
                            }
                            disabled={loading}
                          />
                        </div>

                        <div className="form-control">
                          <label className="label py-1">
                            <span className="label-text text-sm font-medium">
                              Fecha Fin
                            </span>
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
                    </div>
                  </div>

                  {/* Botones de acción en la misma fila */}
                  <div className="flex gap-2 justify-end items-center">
                    <div className="flex gap-2">
                      <button
                        className="btn btn-sm btn-ghost gap-2"
                        onClick={handleClear}
                        disabled={loading}
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
                            Buscar
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Tabla de logs */}
              <TableFileLog
                titles={[
                  "ID",
                  "Usuario",
                  "Tabla",
                  "Operación",
                  "Descripción",
                  "Radicado",
                  "Fecha",
                  "Acciones",
                ]}
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
