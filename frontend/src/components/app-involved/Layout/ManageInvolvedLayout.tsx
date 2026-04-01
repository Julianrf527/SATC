import { useEffect, useState } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import TableInvolved from "../Table/TableInvolved";
import EditInvolvedModal from "../Modal/EditInvolvedModal";

type Involved = {
  id: number;
  numero_documento: number;
  digito_verificacion: string | null;
  tipo_documento: string;
  nombre: string;
  celular: number;
  correo: string;
};

type Props = {
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
};

export default function ManageInvolvedLayout({ setToast }: Props) {
  const rowsPerPage = 10;
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [involved, setInvolved] = useState<Involved[]>([]);
  const [selectedInvolved, setSelectedInvolved] = useState<Involved | null>(null);

  // Filtros
  const [numeroDocumentoFilter, setNumeroDocumentoFilter] = useState("");
  const [tipoDocumentoFilter, setTipoDocumentoFilter] = useState("");
  const [nombreFilter, setNombreFilter] = useState("");
  const [correoFilter, setCorreoFilter] = useState("");

  const hasActiveFilters = !!(numeroDocumentoFilter || tipoDocumentoFilter || nombreFilter || correoFilter);

  const clearFilters = () => {
    setNumeroDocumentoFilter("");
    setTipoDocumentoFilter("");
    setNombreFilter("");
    setCorreoFilter("");
    setPage(1);
  };

  // Cargar involucrados
  useEffect(() => {
    async function loadInvolved() {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        params.append("page", String(page));
        params.append("limit", String(rowsPerPage));
        if (numeroDocumentoFilter.trim()) params.append("numero_documento", numeroDocumentoFilter.trim());
        if (tipoDocumentoFilter) params.append("tipo_documento", tipoDocumentoFilter);
        if (nombreFilter.trim()) params.append("nombre", nombreFilter.trim());
        if (correoFilter.trim()) params.append("correo", correoFilter.trim());

        const res = await apiCall(
          `${API_CONFIG.ENDPOINTS.INVOLVED_MANAGE}?${params.toString()}`,
          { method: "GET" }
        );

        if (res.ok) {
          setInvolved(res.data || []);
          const count = res.totalCount ?? 0;
          setTotalCount(count);
          setTotalPages(count > 0 ? Math.ceil(count / rowsPerPage) : 1);
        } else {
          setToast({ id: Date.now(), message: res.detail || "Error al cargar los involucrados", type: "error" });
        }
      } catch {
        setToast({ id: Date.now(), message: "Error al cargar los datos", type: "error" });
      } finally {
        setLoading(false);
      }
    }
    loadInvolved();
  }, [page, numeroDocumentoFilter, tipoDocumentoFilter, nombreFilter, correoFilter]);

  // Editar involucrado — usa el endpoint INVOLVED_UPDATE del ms dedicado
  const handleSaveEdit = async (
    id: number,
    data: { nombre: string; celular: string; correo: string; digito_verificacion: string }
  ) => {
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.INVOLVED_UPDATE(id), {
        method: "PUT",
        body: JSON.stringify(data),
      });

      if (res.ok) {
        setInvolved((prev) =>
          prev.map((inv) =>
            inv.id === id
              ? { ...inv, nombre: data.nombre, celular: parseInt(data.celular), correo: data.correo, digito_verificacion: data.digito_verificacion || null }
              : inv
          )
        );
        setToast({ id: Date.now(), message: "Involucrado actualizado correctamente", type: "success" });
      } else {
        setToast({ id: Date.now(), message: res.detail || res.message || "No se pudo actualizar el involucrado", type: "error" });
      }
    } catch (e) {
      setToast({ id: Date.now(), message: "Error al actualizar el involucrado", type: "error" });
      throw e;
    }
  };

  return (
    <div className="w-full min-h-[calc(100vh-4rem)] bg-gradient-to-br from-base-200 to-base-300 p-4">
      <div className="max-w-7xl mx-auto space-y-4">

        {/* ── Header ── */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-base-content flex items-center gap-3">
              <div className="w-12 h-12 bg-secondary/10 rounded-xl flex items-center justify-center">
                <svg className="w-7 h-7 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
              </div>
              Gestión de Involucrados
            </h1>
            <p className="text-base-content/60 mt-1">Visualiza y edita la información de los involucrados en los expedientes</p>
          </div>

          {!loading && (
            <div className="stats shadow-sm bg-base-100 border border-base-300">
              <div className="stat py-3 px-5">
                <div className="stat-title text-xs">Total involucrados</div>
                <div className="stat-value text-2xl text-secondary">{totalCount}</div>
                <div className="stat-desc">página {page} de {totalPages}</div>
              </div>
            </div>
          )}
        </div>

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
              <div className="form-control">
                <label className="label py-1"><span className="label-text text-xs">Número Documento</span></label>
                <input type="text" placeholder="Buscar..." className="input input-sm input-bordered"
                  value={numeroDocumentoFilter}
                  onChange={(e) => { setNumeroDocumentoFilter(e.target.value); setPage(1); }} />
              </div>
              <div className="form-control">
                <label className="label py-1"><span className="label-text text-xs">Tipo Documento</span></label>
                <select className="select select-sm select-bordered"
                  value={tipoDocumentoFilter}
                  onChange={(e) => { setTipoDocumentoFilter(e.target.value); setPage(1); }}>
                  <option value="">Todos</option>
                  <option value="CC">CC</option>
                  <option value="CE">CE</option>
                  <option value="NIT">NIT</option>
                  <option value="TI">TI</option>
                  <option value="PAS">PAS</option>
                </select>
              </div>
              <div className="form-control">
                <label className="label py-1"><span className="label-text text-xs">Nombre</span></label>
                <input type="text" placeholder="Buscar..." className="input input-sm input-bordered"
                  value={nombreFilter}
                  onChange={(e) => { setNombreFilter(e.target.value); setPage(1); }} />
              </div>
              <div className="form-control">
                <label className="label py-1"><span className="label-text text-xs">Correo</span></label>
                <input type="text" placeholder="Buscar..." className="input input-sm input-bordered"
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
              titles={["Número Documento", "Tipo", "Nombre", "Celular", "Correo", "Acciones"]}
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
  );
}
