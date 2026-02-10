import { useState, useEffect, useRef } from "react";
import AuditDetailModal from "../AuditDetailModal";

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
  titles: string[];
  data: Auditoria[];
  uniqueTables: string[];
  usuarioFilter: string;
  tablaFilter: string;
  operacionFilter: string;
  idRegistroFilter: string;
  fechaFilter: string;
  onUsuarioFilterChange: (value: string) => void;
  onTablaFilterChange: (value: string) => void;
  onOperacionFilterChange: (value: string) => void;
  onIdRegistroFilterChange: (value: string) => void;
  onFechaFilterChange: (value: string) => void;
  currentPage?: number;
  totalRecords?: number;
  recordsPerPage?: number;
  onPageChange?: (page: number) => void;
  isServerPagination?: boolean;
};

type ModalData = {
  titulo: string;
  tipoOperacion: string;
  tablaAfectada: string;
  datos_anteriores: any;
  datos_nuevos: any;
};

export default function TableUserLog({
  titles,
  data,
  uniqueTables,
  usuarioFilter,
  tablaFilter,
  operacionFilter,
  idRegistroFilter,
  fechaFilter,
  onUsuarioFilterChange,
  onTablaFilterChange,
  onOperacionFilterChange,
  onIdRegistroFilterChange,
  onFechaFilterChange,
  currentPage = 1,
  totalRecords = 0,
  recordsPerPage = 10,
  onPageChange,
  isServerPagination = false,
}: Props) {
  const [modalData, setModalData] = useState<ModalData | null>(null);
  const [page, setPage] = useState(1);
  const rowsPerPage = recordsPerPage;

  // Paginación: usar servidor o cliente según isServerPagination
  const startIndex = isServerPagination ? 0 : (page - 1) * rowsPerPage;
  const endIndex = isServerPagination ? data.length : startIndex + rowsPerPage;
  const paginatedData = isServerPagination ? data : data.slice(startIndex, endIndex);
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

  const openModal = (audit: Auditoria) => {
    setModalData({
      titulo: `Detalles de Auditoría - ${audit.tipo_operacion}`,
      tipoOperacion: audit.tipo_operacion,
      tablaAfectada: audit.tabla_afectada,
      datos_anteriores: audit.datos_anteriores,
      datos_nuevos: audit.datos_nuevos,
    });
  };

  const closeModal = () => {
    setModalData(null);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString("es-CO", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  const getOperationBadge = (operation: string) => {
    const badges: Record<string, string> = {
      INSERT: "badge-success",
      UPDATE: "badge-warning",
      DELETE: "badge-error",
    };
    return badges[operation] || "badge-ghost";
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
    <>
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Contenedor con borde y sombra */}
        <div className="flex flex-col flex-1 overflow-hidden border border-base-300 rounded-lg">
          <div className="overflow-auto">
            <table className="table table-zebra w-full">
              <thead className="sticky top-0 bg-base-200 z-10">
                <tr>
                  {titles.map((title, index) => (
                    <th key={index} className="font-semibold text-center">
                      {title}
                    </th>
                  ))}
                </tr>
                {/* Fila de filtros */}
                <tr className="bg-base-100">
                  <th>
                    <input
                      type="text"
                      placeholder="Filtrar ID..."
                      className="input input-bordered input-sm w-full"
                      disabled
                    />
                  </th>
                  <th>
                    <input
                      type="text"
                      placeholder="Filtrar usuario..."
                      className="input input-bordered input-sm w-full"
                      value={usuarioFilter}
                      onChange={(e) => onUsuarioFilterChange(e.target.value)}
                    />
                  </th>
                  <th>
                    <select
                      className="select select-bordered select-sm w-full"
                      value={tablaFilter}
                      onChange={(e) => onTablaFilterChange(e.target.value)}
                    >
                      <option value="all">Todas</option>
                      {uniqueTables.map((table) => (
                        <option key={table} value={table}>
                          {table}
                        </option>
                      ))}
                    </select>
                  </th>
                  <th>
                    <select
                      className="select select-bordered select-sm w-full"
                      value={operacionFilter}
                      onChange={(e) => onOperacionFilterChange(e.target.value)}
                    >
                      <option value="all">Todas</option>
                      <option value="INSERT">Creación</option>
                      <option value="UPDATE">Actualización</option>
                      <option value="DELETE">Eliminación</option>
                    </select>
                  </th>
                  <th>
                    <input
                      type="text"
                      placeholder="Filtrar descripción..."
                      className="input input-bordered input-sm w-full"
                      disabled
                    />
                  </th>
                  <th>
                    <input
                      type="text"
                      placeholder="Filtrar ID registro..."
                      className="input input-bordered input-sm w-full"
                      value={idRegistroFilter}
                      onChange={(e) => onIdRegistroFilterChange(e.target.value)}
                    />
                  </th>
                  <th>
                    <input
                      type="date"
                      className="input input-bordered input-sm w-full"
                      value={fechaFilter}
                      onChange={(e) => onFechaFilterChange(e.target.value)}
                    />
                  </th>
                  <th>
                    <span className="text-xs">Acciones</span>
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
                        <p className="text-base-content/60 font-medium">
                          No hay registros de auditoría para mostrar
                        </p>
                        <p className="text-sm text-base-content/40">
                          Realice una búsqueda para ver los resultados
                        </p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  paginatedData.map((audit) => {
                    // Determinar si el nombre es un placeholder (Usuario {ID})
                    const isPlaceholder = audit.usuario_nombre.startsWith("Usuario ") && 
                                         !isNaN(Number(audit.usuario_nombre.split(" ")[1]));
                    
                    return (
                    <tr key={audit.id} className="hover">
                      <td className="text-center">{audit.id}</td>
                      <td>
                        <div className="flex flex-col">
                          {isPlaceholder ? (
                            <>
                              <span className="font-semibold text-warning">
                                ID: {audit.usuario_id}
                              </span>
                              <span className="text-xs text-warning/70">
                                ⚠ Nombre no disponible
                              </span>
                            </>
                          ) : (
                            <>
                              <span className="font-semibold">
                                {audit.usuario_nombre}
                              </span>
                              <span className="text-xs opacity-60">
                                ID: {audit.usuario_id}
                              </span>
                              {audit.usuario_correo && (
                                <span className="text-xs opacity-60">
                                  {audit.usuario_correo}
                                </span>
                              )}
                            </>
                          )}
                        </div>
                      </td>
                      <td className="text-center">
                        <span className="badge badge-outline">
                          {audit.tabla_afectada}
                        </span>
                      </td>
                      <td className="text-center">
                        <span
                          className={`badge ${getOperationBadge(
                            audit.tipo_operacion
                          )}`}
                        >
                          {translateOperation(audit.tipo_operacion)}
                        </span>
                      </td>
                      <td>
                        <div
                          className="max-w-xs truncate"
                          title={audit.descripcion}
                        >
                          {audit.descripcion}
                        </div>
                      </td>
                      <td className="text-center">
                        {audit.id_registro || (
                          <span className="text-base-content/40">-</span>
                        )}
                      </td>
                      <td className="text-center text-sm">
                        {formatDate(audit.fecha)}
                      </td>
                      <td className="text-center">
                        <button
                          className="btn btn-ghost btn-xs"
                          onClick={() => openModal(audit)}
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
                              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                            />
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                            />
                          </svg>
                          Ver Detalles
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
                Mostrando {paginatedData.length} de {totalRecords} registro
                {totalRecords !== 1 ? "s" : ""}
                {" (Página "}{displayedPage}{" de "}{totalPages}{")}"}
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
      </div>

      {/* Modal de detalles mejorado */}
      {modalData && (
        <AuditDetailModal
          isOpen={true}
          onClose={closeModal}
          titulo={modalData.titulo}
          tipoOperacion={modalData.tipoOperacion}
          tablaAfectada={modalData.tablaAfectada}
          datosAnteriores={modalData.datos_anteriores}
          datosNuevos={modalData.datos_nuevos}
        />
      )}
    </>
  );
}
