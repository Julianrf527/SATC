import { useEffect, useState, useMemo, useCallback } from "react";
import { apiCall } from "../../../utils/api";
import TitleForm from "../Label/TitleForm";
import TableFiles from "../../app-infracciones/Table/TableFiles";

type Expediente = {
  id: number;
  radicado: string;
  nombre_expediente: string;
  fecha_creacion: string;
  encargado_id: number | null;
  encargado_nombre?: string;
};

type Usuario = {
  id: number;
  nombre: string;
};

interface RespuestaExpedientes {
  ok: boolean;
  data: Expediente[];
  usuarios_disponibles: Usuario[];
  page: number;
  limit: number;
  totalCount: number;
}

type Props = {
  endpoints: {
    lista: string;
    bulkUpdate: string;
  };
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function GestorEncargados({ endpoints, setToast }: Props) {
  const rowsPerPage = 10;
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(false);

  const [expedientes, setExpedientes] = useState<Expediente[]>([]);
  const [usuariosDisponibles, setUsuariosDisponibles] = useState<Usuario[]>([]);
  const [radicadoFilter, setRadicadoFilter] = useState<string>("");
  const [expedienteFilter, setExpedienteFilter] = useState<string>("");
  const [fechaFilter, setFechaFilter] = useState<string>("");
  const [encargadoFilter, setEncargadoFilter] = useState<string>("");
  const [estadoFilter, setEstadoFilter] = useState<string>("all");

  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [selectedEncargadoId, setSelectedEncargadoId] = useState<string>("");
  const [bulkLoading, setBulkLoading] = useState<boolean>(false);

  useEffect(() => {
    async function cargarExpedientes() {
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

        const res = await apiCall(`${endpoints.lista}?${params.toString()}`, {
          method: "GET",
        });
        const data = res as RespuestaExpedientes;

        if (data.ok) {
          setExpedientes(data.data || []);
          setUsuariosDisponibles(data.usuarios_disponibles || []);
          setTotalPages(
            data.totalCount > 0 ? Math.ceil(data.totalCount / rowsPerPage) : 1,
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

    cargarExpedientes();
  }, [
    endpoints.lista,
    page,
    radicadoFilter,
    expedienteFilter,
    fechaFilter,
    setToast,
  ]);

  const handlePageChange = useCallback((newPage: number) => {
    setPage(newPage);
    setSelectedIds(new Set());
  }, []);

  const expedientesFiltrados = useMemo(() => {
    return expedientes.filter((expediente) => {
      const searchTerm = encargadoFilter.toLowerCase().trim();
      const matchesEncargado = !searchTerm
        ? true
        : expediente.encargado_id === null
          ? false
          : (expediente.encargado_nombre?.toLowerCase().includes(searchTerm) ??
              false) ||
            String(expediente.encargado_id).includes(searchTerm);

      const estado = expediente.encargado_id ? "asignado" : "sin_asignar";
      const matchesEstado =
        estadoFilter === "all" ? true : estadoFilter === estado;

      return matchesEncargado && matchesEstado;
    });
  }, [expedientes, encargadoFilter, estadoFilter]);

  const handleSelectionChange = useCallback((id: number, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      checked ? next.add(id) : next.delete(id);
      return next;
    });
  }, []);

  const handleSelectAll = useCallback(
    (checked: boolean) => {
      setSelectedIds(
        checked ? new Set(expedientesFiltrados.map((e) => e.id)) : new Set(),
      );
    },
    [expedientesFiltrados],
  );

  const handleBulkUpdateEncargado = useCallback(async () => {
    if (selectedIds.size === 0 || !selectedEncargadoId) return;

    setBulkLoading(true);
    try {
      const encargadoId = Number(selectedEncargadoId);
      const expedienteIds = Array.from(selectedIds);

      const res = await apiCall(endpoints.bulkUpdate, {
        method: "PATCH",
        body: JSON.stringify({
          expediente_id: expedienteIds,
          encargado_id: encargadoId,
        }),
      });

      if (res.ok) {
        const nuevoEncargado = usuariosDisponibles.find(
          (u) => u.id === encargadoId,
        );
        setExpedientes((prev) =>
          prev.map((e) =>
            selectedIds.has(e.id)
              ? {
                  ...e,
                  encargado_id: encargadoId,
                  encargado_nombre: nuevoEncargado?.nombre,
                }
              : e,
          ),
        );
        setSelectedIds(new Set());
        setSelectedEncargadoId("");
        setToast({
          id: Date.now(),
          message:
            res.msg ||
            `${expedienteIds.length} expediente(s) reasignados correctamente`,
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
  }, [
    endpoints.bulkUpdate,
    selectedIds,
    selectedEncargadoId,
    usuariosDisponibles,
    setToast,
  ]);

  const limpiarFiltros = useCallback(() => {
    setRadicadoFilter("");
    setExpedienteFilter("");
    setFechaFilter("");
    setEncargadoFilter("");
    setEstadoFilter("all");
  }, []);

  const hayFiltrosActivos =
    !!radicadoFilter ||
    !!expedienteFilter ||
    !!fechaFilter ||
    !!encargadoFilter ||
    estadoFilter !== "all";

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

              <div className="bg-base-200 rounded-lg border border-base-300 mb-4">
                <div className="p-4">
                  <div className="grid grid-cols-1 md:grid-cols-5 gap-3 mb-3">
                    {[
                      {
                        label: "Radicado",
                        value: radicadoFilter,
                        onChange: setRadicadoFilter,
                        type: "text",
                        placeholder: "Buscar...",
                      },
                      {
                        label: "Expediente",
                        value: expedienteFilter,
                        onChange: setExpedienteFilter,
                        type: "text",
                        placeholder: "Buscar...",
                      },
                      {
                        label: "Encargado",
                        value: encargadoFilter,
                        onChange: setEncargadoFilter,
                        type: "text",
                        placeholder: "Nombre o cédula",
                      },
                      {
                        label: "Fecha",
                        value: fechaFilter,
                        onChange: setFechaFilter,
                        type: "date",
                        placeholder: "",
                      },
                    ].map(({ label, value, onChange, type, placeholder }) => (
                      <div key={label} className="form-control">
                        <label className="label">
                          <span className="label-text text-xs">{label}</span>
                        </label>
                        <input
                          type={type}
                          placeholder={placeholder}
                          className="input input-sm input-bordered"
                          value={value}
                          onChange={(e) => onChange(e.target.value)}
                        />
                      </div>
                    ))}

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
                          {u.nombre} (CC: {u.id})
                        </option>
                      ))}
                    </select>

                    <span className="text-sm font-medium text-base-content/80 whitespace-nowrap">
                      {selectedIds.size} seleccionados
                    </span>

                    <div className="md:col-span-3 flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-2">
                      <button
                        className="btn btn-sm btn-ghost"
                        disabled={!hayFiltrosActivos}
                        onClick={limpiarFiltros}
                      >
                        Limpiar filtros
                      </button>

                      <button
                        className="btn btn-sm btn-ghost"
                        disabled={selectedIds.size === 0}
                        onClick={() => setSelectedIds(new Set())}
                      >
                        Deseleccionar
                      </button>

                      <button
                        className="btn btn-sm btn-success text-white gap-2"
                        onClick={handleBulkUpdateEncargado}
                        disabled={
                          !selectedEncargadoId ||
                          bulkLoading ||
                          selectedIds.size === 0
                        }
                      >
                        {bulkLoading ? (
                          <span className="loading loading-spinner loading-xs" />
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
                data={expedientesFiltrados}
                encargados={usuariosDisponibles}
                page={page}
                totalPages={totalPages}
                loading={loading}
                onPageChange={handlePageChange}
                selectedIds={selectedIds}
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
