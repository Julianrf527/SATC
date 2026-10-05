import { useEffect, useRef, useState } from "react";
import { getErrorMessage } from "@shared/lib/api";
import CustomSelect from "@shared/ui/form/CustomSelect";
import TableInvolved from "../table/TableInvolved";
import EditInvolvedModal from "../modal/EditInvolvedModal";
import { useInvolvedListQuery, useUpdateInvolvedMutation } from "../api/involved";
import type { Involved, InvolvedSaveData, SetToast } from "../types";

type Props = {
  setToast: SetToast;
};

const EMPTY: Involved[] = [];

export default function ManageInvolvedLayout({ setToast }: Props) {
  const rowsPerPage = 10;
  const [page, setPage] = useState(1);
  const [selectedInvolved, setSelectedInvolved] = useState<Involved | null>(null);

  const [numeroDocumentoFilter, setNumeroDocumentoFilter] = useState("");
  const [tipoDocumentoFilter, setTipoDocumentoFilter] = useState("");
  const [nombreFilter, setNombreFilter] = useState("");
  const [correoFilter, setCorreoFilter] = useState("");

  const listQuery = useInvolvedListQuery({
    page,
    limit: rowsPerPage,
    numeroDocumento: numeroDocumentoFilter,
    tipoDocumento: tipoDocumentoFilter,
    nombre: nombreFilter,
    correo: correoFilter,
  });
  const updateInvolved = useUpdateInvolvedMutation();

  const involved = listQuery.data?.data ?? EMPTY;
  const totalCount = listQuery.data?.totalCount ?? 0;
  const totalPages = totalCount > 0 ? Math.ceil(totalCount / rowsPerPage) : 1;
  const loading = listQuery.isFetching;

  // Toast de error de carga (ref: un setToast inline no debe re-dispararlo).
  const setToastRef = useRef(setToast);
  useEffect(() => {
    setToastRef.current = setToast;
  }, [setToast]);
  useEffect(() => {
    if (!listQuery.error) return;
    setToastRef.current({
      id: Date.now(),
      message: getErrorMessage(listQuery.error, "Error al cargar los involucrados"),
      type: "error",
    });
  }, [listQuery.error]);

  const hasActiveFilters = !!(numeroDocumentoFilter || tipoDocumentoFilter || nombreFilter || correoFilter);

  const clearFilters = () => {
    setNumeroDocumentoFilter("");
    setTipoDocumentoFilter("");
    setNombreFilter("");
    setCorreoFilter("");
    setPage(1);
  };

  // Lanza si falla, para que el modal siga abierto y muestre el error.
  const handleSaveEdit = async (id: number, data: InvolvedSaveData) => {
    try {
      await updateInvolved.mutateAsync({ id, data });
      setToast({ id: Date.now(), message: "Involucrado actualizado correctamente", type: "success" });
    } catch (e) {
      setToast({
        id: Date.now(),
        message: getErrorMessage(e, "No se pudo actualizar el involucrado"),
        type: "error",
      });
      throw e;
    }
  };

  return (
    <>
      <div className="bg-gradient-to-r from-base-100 to-base-200/50 border-b border-base-300 shadow-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-secondary/10 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
              </div>
              <div>
                <p className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wider">
                  Módulo de Involucrados
                </p>
                <h1 className="text-lg font-bold text-base-content">
                  Gestión de Involucrados
                </h1>
                <p className="text-xs text-base-content/60 hidden sm:block">
                  Visualiza y edita la información de los involucrados en los expedientes
                </p>
              </div>
            </div>
            {!loading && (
              <div className="flex items-center gap-3">
                <div className="text-right hidden sm:block">
                  <p className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wider">
                    Total involucrados
                  </p>
                  <p className="text-lg font-bold text-secondary leading-tight">
                    {totalCount}
                    <span className="text-xs font-normal text-base-content/60 ml-1">
                      (pág. {page} de {totalPages})
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

        {/* ── Card: Filtros ── */}
        <div className="card bg-base-100 shadow border border-base-300">
          <div className="card-body p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-semibold text-base-content/70 flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L13 13.414V19a1 1 0 01-.553.894l-4 2A1 1 0 017 21v-7.586L3.293 6.707A1 1 0 013 6V4z" />
                </svg>
                Filtros de búsqueda
                {hasActiveFilters && <span className="badge badge-secondary badge-sm">activos</span>}
              </span>
              <button
                onClick={clearFilters}
                disabled={!hasActiveFilters}
                className={`btn btn-xs gap-1 ${hasActiveFilters ? "btn-error btn-outline" : "btn-ghost opacity-40"}`}
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                Limpiar
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="flex flex-col">
                <label className="label py-1"><span className="text-base-content text-xs">Número Documento</span></label>
                <input type="text" placeholder="Buscar..." className="input input-sm"
                  value={numeroDocumentoFilter}
                  onChange={(e) => { setNumeroDocumentoFilter(e.target.value); setPage(1); }} />
              </div>
              <div className="flex flex-col">
                <label className="label py-1"><span className="text-base-content text-xs">Tipo Documento</span></label>
                <CustomSelect
                  className="select-sm"
                  value={tipoDocumentoFilter}
                  onChange={(v) => { setTipoDocumentoFilter(v); setPage(1); }}
                  emptyValue=""
                  placeholder="Todos"
                  options={[
                    { value: "CC", label: "CC" },
                    { value: "CE", label: "CE" },
                    { value: "NIT", label: "NIT" },
                    { value: "TI", label: "TI" },
                    { value: "PAS", label: "PAS" },
                  ]}
                />
              </div>
              <div className="flex flex-col">
                <label className="label py-1"><span className="text-base-content text-xs">Nombre</span></label>
                <input type="text" placeholder="Buscar..." className="input input-sm"
                  value={nombreFilter}
                  onChange={(e) => { setNombreFilter(e.target.value); setPage(1); }} />
              </div>
              <div className="flex flex-col">
                <label className="label py-1"><span className="text-base-content text-xs">Correo</span></label>
                <input type="text" placeholder="Buscar..." className="input input-sm"
                  value={correoFilter}
                  onChange={(e) => { setCorreoFilter(e.target.value); setPage(1); }} />
              </div>
            </div>
          </div>
        </div>

        {/* ── Card: Tabla ── */}
        <div className="card bg-base-100 shadow border border-base-300">
          <div className="card-body p-4">
            <TableInvolved
              titles={["Número Documento", "Tipo", "Nombre", "Celular", "Correo", "Dirección", "Acciones"]}
              data={involved}
              page={page}
              totalPages={totalPages}
              loading={loading}
              onPageChange={setPage}
              onEdit={(inv) => setSelectedInvolved(inv)}
            />
          </div>
        </div>
      </div>

      {/* Modal de edición */}
      <EditInvolvedModal
        involved={selectedInvolved}
        onClose={() => setSelectedInvolved(null)}
        onSave={handleSaveEdit}
      />
    </div>
    </>
  );
}
