import { useState, useEffect, useRef } from "react";
import AuditDetailModal from "../../app-users/AuditDetailModal";
import CustomSelect from "../../Common/Form/CustomSelect";
import CustomDateInput from "../../Common/Form/CustomDateInput";

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

type Props = {
  titles: string[];
  data: LogAuditoria[];
  uniqueTables: string[];

  usuarioFilter: string;
  tablaFilter: string;
  operacionFilter: string;
  radicadoFilter: string;
  fechaFilter: string;

  onUsuarioFilterChange: (v: string) => void;
  onTablaFilterChange: (v: string) => void;
  onOperacionFilterChange: (v: string) => void;
  onRadicadoFilterChange: (v: string) => void;
  onFechaFilterChange: (v: string) => void;
  auditScope: "sanctioning" | "infraction" | "involved";
  currentPage?: number;
  totalRecords?: number;
  recordsPerPage?: number;
  onPageChange?: (page: number) => void;
  isServerPagination?: boolean;
};

export default function TableFileLog({
  titles,
  data,
  uniqueTables,
  usuarioFilter,
  tablaFilter,
  operacionFilter,
  radicadoFilter,
  fechaFilter,
  onUsuarioFilterChange,
  onTablaFilterChange,
  onOperacionFilterChange,
  onRadicadoFilterChange,
  onFechaFilterChange,
  auditScope,
  currentPage = 1,
  totalRecords = 0,
  recordsPerPage = 10,
  onPageChange,
  isServerPagination = false,
}: Props) {
  const showRadicado = auditScope !== "involved";
  const [modalData, setModalData] = useState<any | null>(null);
  const [page, setPage] = useState(1);
  const rowsPerPage = recordsPerPage;

  // Paginación: usar servidor o cliente según isServerPagination
  const startIndex = isServerPagination ? 0 : (page - 1) * rowsPerPage;
  const endIndex = isServerPagination ? data.length : startIndex + rowsPerPage;
  const paginatedData = isServerPagination
    ? data
    : data.slice(startIndex, endIndex);
  const totalPages = isServerPagination
    ? Math.max(1, Math.ceil(totalRecords / rowsPerPage))
    : Math.max(1, Math.ceil(data.length / rowsPerPage));
  const displayedPage = isServerPagination ? currentPage : page;

  // Resetear página cuando cambian los datos (solo para paginación local)
  const prevDataLength = useRef(data.length);
  useEffect(() => {
    if (!isServerPagination && data.length !== prevDataLength.current) {
      setPage(1);
      prevDataLength.current = data.length;
    }
  }, [data.length, isServerPagination]);

  const openModal = (log: LogAuditoria) => {
    setModalData({
      titulo: `Detalles de Auditoría - ${log.tipo_operacion}`,
      tipoOperacion: log.tipo_operacion,
      tablaAfectada: log.tabla_afectada,
      datos_anteriores: log.datos_anteriores,
      datos_nuevos: log.datos_nuevos,
    });
  };

  const closeModal = () => {
    setModalData(null);
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return "-";
    const date = new Date(dateString);
    return date.toLocaleString("es-CO", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getOperationBadge = (operation: string) => {
    const badges = {
      INSERT: "badge-success",
      UPDATE: "badge-warning",
      DELETE: "badge-error",
      PATCH: "badge-info",
      PUT: "badge-warning",
    };
    return badges[operation as keyof typeof badges] || "badge-ghost";
  };

  const translateOperation = (operation: string): string => {
    const translations: Record<string, string> = {
      INSERT: "Creación",
      UPDATE: "Actualización",
      DELETE: "Eliminación",
    };
    return translations[operation] || operation;
  };

  const handlePreviousPage = () => {
    if (isServerPagination && onPageChange) {
      onPageChange(currentPage - 1);
    } else {
      setPage(page - 1);
    }
  };

  const handleNextPage = () => {
    if (isServerPagination && onPageChange) {
      onPageChange(currentPage + 1);
    } else {
      setPage(page + 1);
    }
  };

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Contenedor con borde y sombra */}
      <div className="flex flex-col flex-1 overflow-hidden border border-base-300 rounded-lg">
        <div className="overflow-auto">
          <table className="table table-zebra w-full">
            <thead className="sticky top-0 bg-base-200 z-10">
              <tr>
                {titles.map((title, index) => (
                  <th key={index} className="font-semibold">
                    {title}
                  </th>
                ))}
              </tr>
              {/* Fila de filtros */}
              <tr className="bg-base-100">
                <th>
                  <input
                    className="input input-bordered input-sm w-full"
                    placeholder="Filtrar usuario..."
                    value={usuarioFilter}
                    onChange={(e) => onUsuarioFilterChange(e.target.value)}
                  />
                </th>
                <th>
                  <CustomSelect
                    className="select-sm"
                    hidePlaceholderOption
                    value={tablaFilter}
                    onChange={onTablaFilterChange}
                    options={[
                      { value: "all", label: "Todas" },
                      ...uniqueTables.map((table) => ({ value: table, label: table })),
                    ]}
                  />
                </th>
                <th>
                  <CustomSelect
                    className="select-sm"
                    hidePlaceholderOption
                    value={operacionFilter}
                    onChange={onOperacionFilterChange}
                    options={[
                      { value: "all", label: "Todas" },
                      { value: "INSERT", label: "Creación" },
                      { value: "UPDATE", label: "Actualización" },
                      { value: "DELETE", label: "Eliminación" },
                    ]}
                  />
                </th>
                <th>
                  <div className="text-xs text-base-content/60">-</div>
                </th>
                {showRadicado && (
                  <th>
                    <input
                      className="input input-bordered input-sm w-full"
                      placeholder="Filtrar radicado..."
                      value={radicadoFilter}
                      onChange={(e) => onRadicadoFilterChange(e.target.value)}
                    />
                  </th>
                )}
                <th>
                  <CustomDateInput
                    className="input-sm"
                    value={fechaFilter}
                    onChange={onFechaFilterChange}
                  />
                </th>
                <th>
                  <div className="text-xs text-base-content/60">-</div>
                </th>
              </tr>
            </thead>
            <tbody>
              {paginatedData.length === 0 ? (
                <tr>
                  <td colSpan={titles.length} className="text-center py-12">
                    <div className="flex flex-col items-center gap-2">
                      <svg
                        className="w-12 h-12 text-base-content/30"
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
                      <span className="text-base-content/60 font-medium">
                        No hay logs de auditoría
                      </span>
                      <span className="text-base-content/40 text-sm">
                        Realiza una búsqueda o ajusta los filtros
                      </span>
                    </div>
                  </td>
                </tr>
              ) : (
                paginatedData.map((log) => {
                  // Determinar si el nombre es un placeholder (Usuario {ID})
                  const usuarioNombre = log.usuario_nombre || "";
                  const isPlaceholder =
                    usuarioNombre.startsWith("Usuario ") &&
                    !isNaN(Number(usuarioNombre.split(" ")[1]));

                  return (
                    <tr key={log.id} className="hover">
                      <td>
                        <div className="flex flex-col">
                          {isPlaceholder ? (
                            <>
                              <span className="font-medium text-warning">
                                {log.usuario_documento || "Usuario desconocido"}
                              </span>
                              <span className="text-xs text-warning/70">
                                ⚠ Nombre no disponible
                              </span>
                            </>
                          ) : (
                            <>
                              <span className="font-medium">
                                {log.usuario_nombre}
                              </span>
                              {log.usuario_documento && (
                                <span className="text-xs text-base-content/60">
                                  {log.usuario_documento}
                                </span>
                              )}
                            </>
                          )}
                        </div>
                      </td>
                      <td>
                        <span className="badge badge-outline">
                          {log.tabla_afectada}
                        </span>
                      </td>
                      <td>
                        <span
                          className={`badge ${getOperationBadge(
                            log.tipo_operacion,
                          )} text-white`}
                        >
                          {translateOperation(log.tipo_operacion)}
                        </span>
                      </td>
                      <td className="max-w-xs truncate" title={log.descripcion}>
                        {log.descripcion}
                      </td>
                      {showRadicado && (
                        <td>
                          {log.expediente_radicado ? (
                            <span className="font-mono text-sm">
                              {log.expediente_radicado}
                            </span>
                          ) : (
                            <span className="text-base-content/40">-</span>
                          )}
                        </td>
                      )}
                      <td className="text-sm">{formatDate(log.fecha)}</td>
                      <td>
                        <button
                          className="btn btn-ghost btn-sm"
                          onClick={() => openModal(log)}
                          title="Ver detalles"
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
                              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                            />
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                            />
                          </svg>
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Paginación */}
      <div className="flex justify-between items-center pt-4 border-t border-base-300 mt-4">
        <div className="text-sm text-base-content/60">
          {isServerPagination ? (
            <>
              Mostrando {paginatedData.length} de {totalRecords} registros
            </>
          ) : (
            <>
              Mostrando {paginatedData.length} de {data.length} registro
              {data.length !== 1 ? "s" : ""}
            </>
          )}
        </div>
        <div className="join">
          <button
            className="join-item btn btn-sm"
            disabled={displayedPage === 1 || data.length === 0}
            onClick={handlePreviousPage}
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
                d="M15 19l-7-7 7-7"
              />
            </svg>
          </button>
          <button className="join-item btn btn-sm no-animation">
            Página {data.length === 0 ? 0 : displayedPage} de {totalPages}
          </button>
          <button
            className="join-item btn btn-sm"
            disabled={displayedPage >= totalPages || data.length === 0}
            onClick={handleNextPage}
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
                d="M9 5l7 7-7 7"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Modal de detalles con AuditDetailModal */}
      {modalData && (
        <AuditDetailModal
          isOpen={!!modalData}
          onClose={closeModal}
          titulo={modalData.titulo}
          tipoOperacion={modalData.tipoOperacion}
          tablaAfectada={modalData.tablaAfectada}
          datosAnteriores={modalData.datos_anteriores}
          datosNuevos={modalData.datos_nuevos}
          auditScope={auditScope}
        />
      )}
    </div>
  );
}
