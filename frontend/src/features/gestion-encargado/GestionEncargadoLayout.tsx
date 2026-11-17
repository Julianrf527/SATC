import { useEffect, useRef, useState, useMemo, useCallback } from "react";
import { Users } from "lucide-react";
import { ApiError } from "@shared/lib/api";
import TableFiles from "./TableFiles";
import EncargadoFiltrosPanel from "./EncargadoFiltrosPanel";
import {
  useBulkUpdateEncargadoMutation,
  useExpedientesEncargadoQuery,
} from "./api/expedientes";
import type { ExpedienteEncargado, GestionEncargadoEndpoints, SetToast, UsuarioEncargado } from "./types";

type Props = {
  endpoints: GestionEncargadoEndpoints;
  title: string;
  modulo: string;
  showExpediente?: boolean;
  setToast: SetToast;
};

const EMPTY_EXPEDIENTES: ExpedienteEncargado[] = [];
const EMPTY_USUARIOS: UsuarioEncargado[] = [];

export default function GestorEncargados({ endpoints, title, modulo, showExpediente = true, setToast }: Props) {
  const rowsPerPage = 10;
  const [page, setPage] = useState<number>(1);

  const [radicadoFilter, setRadicadoFilter] = useState<string>("");
  const [expedienteFilter, setExpedienteFilter] = useState<string>("");
  const [fechaFilter, setFechaFilter] = useState<string>("");
  const [encargadoFilter, setEncargadoFilter] = useState<string>("");
  const [estadoFilter, setEstadoFilter] = useState<string>("all");

  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [selectedEncargadoId, setSelectedEncargadoId] = useState<string>("");

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

  const listQuery = useExpedientesEncargadoQuery(endpoints.lista, {
    page,
    limit: rowsPerPage,
    radicado: debouncedRadicadoFilter,
    nombreExpediente: showExpediente ? debouncedExpedienteFilter : "",
    fechaCreacion: debouncedFechaFilter,
  });
  const bulkUpdate = useBulkUpdateEncargadoMutation(endpoints.bulkUpdate, endpoints.lista);

  const expedientes = listQuery.data?.data ?? EMPTY_EXPEDIENTES;
  const usuariosDisponibles = listQuery.data?.usuarios_disponibles ?? EMPTY_USUARIOS;
  const totalCount = listQuery.data?.totalCount ?? 0;
  const totalPages = totalCount > 0 ? Math.ceil(totalCount / rowsPerPage) : 1;
  const loading = listQuery.isFetching;
  const bulkLoading = bulkUpdate.isPending;

  // Toast de error de carga (ref para no re-disparar si `setToast` cambia).
  const setToastRef = useRef(setToast);
  useEffect(() => {
    setToastRef.current = setToast;
  }, [setToast]);
  useEffect(() => {
    if (!listQuery.error) return;
    setToastRef.current({
      id: Date.now(),
      message:
        listQuery.error instanceof ApiError
          ? "Error en la respuesta del servidor"
          : "Error al cargar los datos",
      type: "error",
    });
  }, [listQuery.error]);

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
      if (checked) next.add(id);
      else next.delete(id);
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

  const handleBulkUpdateEncargado = useCallback(() => {
    if (selectedIds.size === 0 || !selectedEncargadoId) return;
    const expedienteIds = Array.from(selectedIds);
    bulkUpdate.mutate(
      { expedienteIds, encargadoId: Number(selectedEncargadoId) },
      {
        onSuccess: (res) => {
          setSelectedIds(new Set());
          setSelectedEncargadoId("");
          setToast({
            id: Date.now(),
            message: res.msg || `${expedienteIds.length} expediente(s) reasignados correctamente`,
            type: "success",
          });
        },
        onError: () => {
          setToast({ id: Date.now(), message: "No se pudo actualizar el encargado", type: "error" });
        },
      },
    );
  }, [bulkUpdate, selectedIds, selectedEncargadoId, setToast]);

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
                <p className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wider">
                  {modulo}
                </p>
                <h1 className="text-lg font-bold text-base-content">{title}</h1>
              </div>
            </div>
            {!loading && (
              <div className="flex items-center gap-3">
                <div className="text-right hidden sm:block">
                  <p className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wider">
                    Total expedientes
                  </p>
                  <p className="text-lg font-bold text-success leading-tight">
                    {expedientes.length}
                    <span className="text-xs font-normal text-base-content/60 ml-1">
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
        <EncargadoFiltrosPanel
          showExpediente={showExpediente}
          radicadoFilter={radicadoFilter}
          expedienteFilter={expedienteFilter}
          encargadoFilter={encargadoFilter}
          fechaFilter={fechaFilter}
          estadoFilter={estadoFilter}
          onRadicadoFilterChange={setRadicadoFilter}
          onExpedienteFilterChange={setExpedienteFilter}
          onEncargadoFilterChange={setEncargadoFilter}
          onFechaFilterChange={setFechaFilter}
          onEstadoFilterChange={setEstadoFilter}
          usuariosDisponibles={usuariosDisponibles}
          selectedEncargadoId={selectedEncargadoId}
          onSelectedEncargadoIdChange={setSelectedEncargadoId}
          selectedCount={selectedIds.size}
          hayFiltrosActivos={hayFiltrosActivos}
          bulkLoading={bulkLoading}
          onLimpiarFiltros={limpiarFiltros}
          onDeseleccionar={() => setSelectedIds(new Set())}
          onCambiarEncargado={handleBulkUpdateEncargado}
        />

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
