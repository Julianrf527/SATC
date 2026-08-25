import { useEffect, useState, useMemo, useCallback } from "react";
import { Users } from "lucide-react";
import { apiCall } from "../../../utils/api";
import TableFiles from "../../app-infraccion/Table/TableFiles";
import CustomSelect from "../Form/CustomSelect";

type Expediente = {
  id: number;
  radicado: string;
  nombre_expediente: string;
  fecha_creacion: string;
  encargado_id: number | null;
  encargado_nombre?: string;
  encargado_documento?: string | number;
};

type Usuario = {
  id: number;
  nombre: string;
  numero_documento?: string | number;
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
  title: string;
  modulo: string;
  showExpediente?: boolean;
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function GestorEncargados({ endpoints, title, modulo, showExpediente = true, setToast }: Props) {
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

  const [debouncedRadicadoFilter, setDebouncedRadicadoFilter] = useState(radicadoFilter);
  const [debouncedExpedienteFilter, setDebouncedExpedienteFilter] = useState(expedienteFilter);
  const [debouncedFechaFilter, setDebouncedFechaFilter] = useState(fechaFilter);

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      setDebouncedRadicadoFilter(radicadoFilter);
      setDebouncedExpedienteFilter(expedienteFilter);
      setDebouncedFechaFilter(fechaFilter);
    }, 400);

    return () => clearTimeout(timeoutId);
  }, [radicadoFilter, expedienteFilter, fechaFilter]);

  useEffect(() => {
    async function cargarExpedientes() {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        params.append("page", String(page));
        params.append("limit", String(rowsPerPage));
        if (debouncedRadicadoFilter.trim())
          params.append("radicado", debouncedRadicadoFilter.trim());
        if (showExpediente && debouncedExpedienteFilter.trim())
          params.append("nombre_expediente", debouncedExpedienteFilter.trim());
        if (debouncedFechaFilter.trim())
          params.append("fecha_creacion", debouncedFechaFilter.trim());

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
    debouncedRadicadoFilter,
    debouncedExpedienteFilter,
    debouncedFechaFilter,
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
        const updatedIds = new Set<number>(
          (res.updated as { id: number }[] | undefined)?.map((u) => u.id) ?? [],
        );
        setExpedientes((prev) =>
          prev.map((e) =>
            updatedIds.has(e.id)
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
    <>
      <div className="bg-gradient-to-r from-base-100 to-base-200/50 border-b border-base-300 shadow-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
                <Users className="text-success" size={20} />
              </div>
              <div>
                <p className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wider">
                  {modulo}
                </p>
                <h1 className="text-lg font-bold text-base-content">{title}</h1>
              </div>
            </div>
            {!loading && (
              <div className="flex items-center gap-3">
                <div className="text-right hidden sm:block">
                  <p className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wider">
                    Total expedientes
                  </p>
                  <p className="text-lg font-bold text-success leading-tight">
                    {expedientes.length}
                    <span className="text-xs font-normal text-base-content/50 ml-1">
                      ({expedientesFiltrados.length} visibles)
                    </span>
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="w-full min-h-[calc(100vh-4rem)] bg-gradient-to-br from-base-200 to-base-300 p-4">
        <div className="max-w-7xl mx-auto space-y-4">
        <div className="card bg-base-100 shadow border border-base-300">
          <div className="card-body p-4">
            <div className={`grid grid-cols-1 gap-3 mb-3 ${showExpediente ? "md:grid-cols-5" : "md:grid-cols-4"}`}>
              {[
                {
                  label: "Radicado",
                  value: radicadoFilter,
                  onChange: setRadicadoFilter,
                  type: "text",
                  placeholder: "Buscar...",
                  show: true,
                },
                {
                  label: "Expediente",
                  value: expedienteFilter,
                  onChange: setExpedienteFilter,
                  type: "text",
                  placeholder: "Buscar...",
                  show: showExpediente,
                },
                {
                  label: "Encargado",
                  value: encargadoFilter,
                  onChange: setEncargadoFilter,
                  type: "text",
                  placeholder: "Nombre o cédula",
                  show: true,
                },
                {
                  label: "Fecha",
                  value: fechaFilter,
                  onChange: setFechaFilter,
                  type: "date",
                  placeholder: "",
                  show: true,
                },
              ].filter((f) => f.show).map(({ label, value, onChange, type, placeholder }) => (
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
                <CustomSelect
                  className="select-sm"
                  hidePlaceholderOption
                  value={estadoFilter}
                  onChange={setEstadoFilter}
                  options={[
                    { value: "all", label: "Todos" },
                    { value: "asignado", label: "Asignados" },
                    { value: "sin_asignar", label: "Sin asignar" },
                  ]}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-5 gap-3 rounded-lg mb-2 items-center">
              <CustomSelect
                className="select-sm h-9"
                value={selectedEncargadoId}
                onChange={setSelectedEncargadoId}
                emptyValue=""
                placeholder="Seleccionar encargado..."
                options={usuariosDisponibles.map((u) => ({
                  value: String(u.id),
                  label: `${u.nombre} (CC: ${u.numero_documento ?? u.id})`,
                }))}
              />

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

        <div className="card bg-base-100 shadow border border-base-300">
          <div className="card-body p-4">
            <TableFiles
              titles={[
                "Radicado",
                ...(showExpediente ? ["Expediente"] : []),
                "Fecha",
                "Encargado",
                "Estado",
              ]}
              showExpediente={showExpediente}
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
      </div>
    </>
  );
}
