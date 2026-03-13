import { useEffect, useState, useMemo, useCallback } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import TitleForm from "../../Label/TitleForm";
import TableFiles from "../Table/TableFiles";

type File = {
  radicado: string;
  nombre_expediente: string;
  fecha_creacion: string;
  encargado_id: number | null;
  encargado_nombre?: string;
};

type User = {
  id: number;
  name: string;
};

interface FilesResponse {
  ok: boolean;
  data: File[];
  usuarios_disponibles: User[];
  page: number;
  limit: number;
  totalCount: number;
}

type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function ManagerFiles({ setToast }: Props) {
  const rowsPerPage = 10;
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(false);

  const [files, setFiles] = useState<File[]>([]);
  const [usuariosDisponibles, setUsuariosDisponibles] = useState<User[]>([]);
  const [radicadoFilter, setRadicadoFilter] = useState<string>("");
  const [expedienteFilter, setExpedienteFilter] = useState<string>("");
  const [fechaFilter, setFechaFilter] = useState<string>("");
  const [encargadoFilter, setEncargadoFilter] = useState<string>("");
  const [estadoFilter, setEstadoFilter] = useState<string>("all");

  // Selección bulk
  const [selectedRadicados, setSelectedRadicados] = useState<Set<string>>(
    new Set(),
  );
  const [selectedEncargadoId, setSelectedEncargadoId] = useState<string>("");
  const [bulkLoading, setBulkLoading] = useState<boolean>(false);

  // Cargar expedientes
  useEffect(() => {
    async function loadFiles() {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        params.append("page", String(page));
        params.append("limit", String(rowsPerPage));

        if (radicadoFilter.trim())
          params.append("radicado", radicadoFilter.trim());
        if (expedienteFilter.trim())
          params.append("nombre_expediente", expedienteFilter.trim());
        if (fechaFilter.trim())
          params.append("fecha_creacion", fechaFilter.trim());

        const resFiles = await apiCall(
          `${API_CONFIG.ENDPOINTS.FILES}?${params.toString()}`,
          { method: "GET" },
        );
        const filesData = resFiles as FilesResponse;

        if (filesData.ok) {
          setFiles(filesData.data || []);
          setUsuariosDisponibles(filesData.usuarios_disponibles || []);
          setTotalPages(
            filesData.totalCount > 0
              ? Math.ceil(filesData.totalCount / rowsPerPage)
              : 1,
          );
        } else {
          setToast({
            id: Date.now(),
            message: "Error en la respuesta del servidor",
            type: "error",
          });
        }
      } catch {
        setToast({
          id: Date.now(),
          message: "Error al cargar los datos",
          type: "error",
        });
      } finally {
        setLoading(false);
      }
    }

    loadFiles();
  }, [page, radicadoFilter, expedienteFilter, fechaFilter, setToast]);

  // Limpiar selección al cambiar de página
  const handlePageChange = useCallback((newPage: number) => {
    setPage(newPage);
    setSelectedRadicados(new Set());
  }, []);

  // Filtrado en el cliente
  const filteredFiles = useMemo(() => {
    return files.filter((f) => {
      const searchTerm = encargadoFilter.toLowerCase().trim();
      const matchesEncargado = !searchTerm
        ? true
        : f.encargado_id === null
          ? false
          : (f.encargado_nombre?.toLowerCase().includes(searchTerm) ?? false) ||
            String(f.encargado_id).includes(searchTerm);

      const estado = f.encargado_id ? "asignado" : "sin_asignar";
      const matchesEstado =
        estadoFilter === "all" ? true : estadoFilter === estado;

      return matchesEncargado && matchesEstado;
    });
  }, [files, encargadoFilter, estadoFilter]);

  // Selección individual
  const handleSelectionChange = useCallback(
    (radicado: string, checked: boolean) => {
      setSelectedRadicados((prev) => {
        const next = new Set(prev);
        checked ? next.add(radicado) : next.delete(radicado);
        return next;
      });
    },
    [],
  );

  // Seleccionar todos los de la página actual
  const handleSelectAll = useCallback(
    (checked: boolean) => {
      if (checked) {
        setSelectedRadicados(new Set(filteredFiles.map((f) => f.radicado)));
      } else {
        setSelectedRadicados(new Set());
      }
    },
    [filteredFiles],
  );

  // Cambio masivo de encargado
  const handleBulkUpdateEncargado = useCallback(async () => {
    if (selectedRadicados.size === 0 || !selectedEncargadoId) return;

    setBulkLoading(true);
    try {
      const encargadoId = Number(selectedEncargadoId);
      const radicadosList = Array.from(selectedRadicados);

      const res = await apiCall(
        API_CONFIG.ENDPOINTS.FILE_BULK_UPDATE_ENCARGADO,
        {
          method: "PATCH",
          body: JSON.stringify({
            radicados: radicadosList,
            encargado_id: encargadoId,
          }),
        },
      );

      if (res.ok) {
        const nuevoEncargado = usuariosDisponibles.find(
          (u) => u.id === encargadoId,
        );
        setFiles((prev) =>
          prev.map((f) =>
            selectedRadicados.has(f.radicado)
              ? {
                  ...f,
                  encargado_id: encargadoId,
                  encargado_nombre: nuevoEncargado?.name,
                }
              : f,
          ),
        );
        setSelectedRadicados(new Set());
        setSelectedEncargadoId("");
        setToast({
          id: Date.now(),
          message:
            res.msg ||
            `${radicadosList.length} expediente(s) reasignados correctamente`,
          type: "success",
        });
      } else {
        setToast({
          id: Date.now(),
          message: "No se pudo actualizar el encargado",
          type: "error",
        });
      }
    } catch {
      setToast({
        id: Date.now(),
        message: "No se pudo actualizar el encargado",
        type: "error",
      });
    } finally {
      setBulkLoading(false);
    }
  }, [selectedRadicados, selectedEncargadoId, usuariosDisponibles, setToast]);

  return (
    <div className="bg-base-200">
      <section className="w-full h-full flex justify-center items-start min-h-[calc(100vh-4rem)] overflow-hidden p-4">
        <div className="w-full max-w-6xl h-full">
          <div className="card bg-base-100 shadow-xl border border-base-300 w-full h-full">
            <div className="card-body px-6 py-6 flex flex-col h-full overflow-hidden">
              <TitleForm
                title="Gestionar Expedientes"
                body="Filtra y asigna encargados."
              />

              {/* Panel de filtros y tools */}
              <div className="bg-base-200 rounded-lg border border-base-300 mb-4">
                <div className="p-4">
                  <div className="grid grid-cols-1 md:grid-cols-5 gap-3 mb-3">
                    <div className="form-control">
                      <label className="label">
                        <span className="label-text text-xs">Radicado</span>
                      </label>
                      <input
                        type="text"
                        placeholder="Buscar..."
                        className="input input-sm input-bordered"
                        value={radicadoFilter}
                        onChange={(e) => setRadicadoFilter(e.target.value)}
                      />
                    </div>
                    <div className="form-control">
                      <label className="label">
                        <span className="label-text text-xs">Expediente</span>
                      </label>
                      <input
                        type="text"
                        placeholder="Buscar..."
                        className="input input-sm input-bordered"
                        value={expedienteFilter}
                        onChange={(e) => setExpedienteFilter(e.target.value)}
                      />
                    </div>

                    <div className="form-control">
                      <label className="label">
                        <span className="label-text text-xs">Encargado</span>
                      </label>
                      <input
                        type="text"
                        placeholder="Nombre o cédula"
                        className="input input-sm input-bordered"
                        value={encargadoFilter}
                        onChange={(e) => setEncargadoFilter(e.target.value)}
                      />
                    </div>
                    <div className="form-control">
                      <label className="label">
                        <span className="label-text text-xs">Fecha</span>
                      </label>
                      <input
                        type="date"
                        className="input input-sm input-bordered"
                        value={fechaFilter}
                        onChange={(e) => setFechaFilter(e.target.value)}
                      />
                    </div>
                    <div className="form-control">
                      <label className="label">
                        <span className="label-text text-xs">Estado</span>
                      </label>
                      <select
                        className="select select-sm select-bordered"
                        value={estadoFilter}
                        onChange={(e) => setEstadoFilter(e.target.value)}
                      >
                        <option value="all">Todos</option>
                        <option value="asignado">Asignados</option>
                        <option value="sin_asignar">Sin asignar</option>
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-5 gap-3 bg-base-200 rounded-lg mb-2 items-center">
                    <select
                      className="select select-sm select-bordered w-full h-9"
                      value={selectedEncargadoId}
                      onChange={(e) => setSelectedEncargadoId(e.target.value)}
                    >
                      <option value="">Seleccionar encargado...</option>
                      {usuariosDisponibles.map((u) => (
                        <option key={u.id} value={u.id}>
                          {u.name} (CC: {u.id})
                        </option>
                      ))}
                    </select>

                    <span className="text-sm font-medium text-base-content/80 whitespace-nowrap">
                      {selectedRadicados.size} seleccionados
                    </span>

                    <div className="md:col-span-3 flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-2">
                      <button
                        className="btn btn-sm btn-ghost"
                        disabled={
                          !radicadoFilter &&
                          !expedienteFilter &&
                          !fechaFilter &&
                          !encargadoFilter &&
                          estadoFilter === "all"
                        }
                        onClick={() => {
                          setRadicadoFilter("");
                          setExpedienteFilter("");
                          setFechaFilter("");
                          setEncargadoFilter("");
                          setEstadoFilter("all");
                        }}
                      >
                        Limpiar filtros
                      </button>

                      <button
                        className="btn btn-sm btn-ghost"
                        disabled={selectedRadicados.size === 0}
                        onClick={() => setSelectedRadicados(new Set())}
                      >
                        Deseleccionar
                      </button>

                      <button
                        className="btn btn-sm btn-success text-white gap-2"
                        onClick={handleBulkUpdateEncargado}
                        disabled={
                          !selectedEncargadoId ||
                          bulkLoading ||
                          selectedRadicados.size === 0
                        }
                      >
                        {bulkLoading ? (
                          <span className="loading loading-spinner loading-xs"></span>
                        ) : (
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
                              d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                            />
                          </svg>
                        )}
                        Cambiar Encargado
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <TableFiles
                titles={[
                  "Radicado",
                  "Expediente",
                  "Fecha",
                  "Encargado",
                  "Estado",
                ]}
                data={filteredFiles}
                encargados={usuariosDisponibles}
                page={page}
                totalPages={totalPages}
                loading={loading}
                onPageChange={handlePageChange}
                selectedRadicados={selectedRadicados}
                onSelectionChange={handleSelectionChange}
                onSelectAll={handleSelectAll}
              />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
