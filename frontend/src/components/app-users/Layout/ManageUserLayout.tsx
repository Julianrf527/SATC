import { useEffect, useMemo, useState } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import TableUsers from "../../app-users/Table/TableUsers";

type User = {
  id: number;
  document: number;
  name: string;
  email: string;
  rol_id: number;
  state: boolean;
};

type Role = { id: number; name: string };

type Props = {
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
};

export default function ManageUserLayout({ setToast }: Props) {
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);

  const [documentFilter, setDocumentFilter] = useState("");
  const [nameFilter, setNameFilter] = useState("");
  const [emailFilter, setEmailFilter] = useState("");
  const [stateFilter, setStateFilter] = useState("all");
  const [roleFilter, setRoleFilter] = useState("all");

  const buildFullName = (a: string, b: string | null, c: string, d: string | null) =>
    [a, b, c, d].filter(Boolean).join(" ");

  useEffect(() => {
    async function loadUsers() {
      try {
        const res = await apiCall(API_CONFIG.ENDPOINTS.USERS, { method: "GET" });
        if (!res.ok) {
          setToast({ id: Date.now(), message: res.detail || res.msg || "Error al cargar los usuarios", type: "error" });
        } else {
          setUsers((res.data || []).map((u: any) => ({
            id: u.id,
            document: u.numero_documento,
            name: buildFullName(u.primer_nombre, u.segundo_nombre, u.primer_apellido, u.segundo_apellido),
            email: u.correo,
            rol_id: u.rol_id,
            state: typeof u.state !== "undefined" ? u.state : false,
          })));
        }
      } catch {
        setToast({ id: Date.now(), message: "Error al cargar los usuarios", type: "error" });
      }
    }
    async function loadRoles() {
      try {
        const res = await apiCall(API_CONFIG.ENDPOINTS.ROL_LIST, { method: "GET" });
        if (res.ok) setRoles(res.data || []);
      } catch { /* silence */ }
    }
    Promise.all([loadUsers(), loadRoles()]).finally(() => setLoading(false));
  }, []);

  const filteredUsers = useMemo(() => {
    const doc = documentFilter.trim();
    const name = nameFilter.trim().toLowerCase();
    const email = emailFilter.trim().toLowerCase();
    return users.filter((u) => {
      const matchesDoc = doc ? String(u.document).includes(doc) : true;
      const matchesName = name ? u.name.toLowerCase().includes(name) : true;
      const matchesEmail = email ? u.email.toLowerCase().includes(email) : true;
      const matchesState = stateFilter === "all" ? true : stateFilter === "active" ? u.state : !u.state;
      const matchesRole = roleFilter === "all" ? true : u.rol_id === Number(roleFilter);
      return matchesDoc && matchesName && matchesEmail && matchesState && matchesRole;
    });
  }, [users, documentFilter, nameFilter, emailFilter, stateFilter, roleFilter]);

  const toggleState = async (id: number) => {
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.USER_TOGGLE_STATE(id), { method: "PATCH" });
      if (res.ok) {
        setUsers((prev) => prev.map((u) => (u.id === id ? { ...u, state: !u.state } : u)));
        setToast({ id: Date.now(), message: "Estado actualizado correctamente", type: "success" });
      } else {
        setToast({ id: Date.now(), message: res.detail || res.msg || "No se pudo actualizar el estado", type: "error" });
      }
    } catch {
      setToast({ id: Date.now(), message: "No se pudo actualizar el estado", type: "error" });
    }
  };

  const toggleRol = async (id: number, newRol: number) => {
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.USER_TOGGLE_ROLE(id, newRol), { method: "PATCH" });
      if (res.ok) {
        setUsers((prev) => prev.map((u) => (u.id === id ? { ...u, rol_id: newRol } : u)));
        setToast({ id: Date.now(), message: res.msg || "Rol actualizado correctamente", type: "success" });
      } else {
        setToast({ id: Date.now(), message: res.detail || res.msg || "No se pudo actualizar el rol", type: "error" });
      }
    } catch {
      setToast({ id: Date.now(), message: "No se pudo actualizar el rol", type: "error" });
    }
  };

  const clearFilters = () => {
    setDocumentFilter(""); setNameFilter(""); setEmailFilter("");
    setStateFilter("all"); setRoleFilter("all");
  };

  const hasActiveFilters =
    documentFilter.trim() !== "" || nameFilter.trim() !== "" ||
    emailFilter.trim() !== "" || roleFilter !== "all" || stateFilter !== "all";

  return (
    <div className="w-full min-h-[calc(100vh-4rem)] bg-gradient-to-br from-base-200 to-base-300 p-4">
      <div className="max-w-7xl mx-auto space-y-4">

        {/* ── Header ── */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-base-content flex items-center gap-3">
              <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center">
                <svg className="w-7 h-7 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              Gestión de Usuarios
            </h1>
            <p className="text-base-content/60 mt-1">Administra roles y estados de los usuarios del sistema</p>
          </div>
          {!loading && (
            <div className="stats shadow-sm bg-base-100 border border-base-300">
              <div className="stat py-3 px-5">
                <div className="stat-title text-xs">Total usuarios</div>
                <div className="stat-value text-2xl text-primary">{users.length}</div>
                <div className="stat-desc">{filteredUsers.length} visibles</div>
              </div>
            </div>
          )}
        </div>

        {loading ? (
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="text-center">
              <span className="loading loading-spinner loading-lg text-primary" />
              <p className="mt-4 text-base-content/60">Cargando usuarios...</p>
            </div>
          </div>
        ) : (
          <>
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
                    {hasActiveFilters && <span className="badge badge-primary badge-sm">activos</span>}
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

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
                  <div className="form-control">
                    <label className="label py-1"><span className="label-text text-xs">Cédula</span></label>
                    <input type="text" placeholder="Buscar..." className="input input-sm input-bordered"
                      value={documentFilter} onChange={(e) => setDocumentFilter(e.target.value)} />
                  </div>
                  <div className="form-control">
                    <label className="label py-1"><span className="label-text text-xs">Nombre</span></label>
                    <input type="text" placeholder="Buscar..." className="input input-sm input-bordered"
                      value={nameFilter} onChange={(e) => setNameFilter(e.target.value)} />
                  </div>
                  <div className="form-control">
                    <label className="label py-1"><span className="label-text text-xs">Correo</span></label>
                    <input type="text" placeholder="Buscar..." className="input input-sm input-bordered"
                      value={emailFilter} onChange={(e) => setEmailFilter(e.target.value)} />
                  </div>
                  <div className="form-control">
                    <label className="label py-1"><span className="label-text text-xs">Rol</span></label>
                    <select className="select select-sm select-bordered"
                      value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
                      <option value="all">Todos</option>
                      {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                    </select>
                  </div>
                  <div className="form-control">
                    <label className="label py-1"><span className="label-text text-xs">Estado</span></label>
                    <select className="select select-sm select-bordered"
                      value={stateFilter} onChange={(e) => setStateFilter(e.target.value)}>
                      <option value="all">Todos</option>
                      <option value="active">Activos</option>
                      <option value="inactive">Inactivos</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>

            {/* ── Card: Tabla ── */}
            <div className="card bg-base-100 shadow border border-base-300">
              <div className="card-body p-4">
                <TableUsers
                  titles={["Cédula", "Nombre", "Correo", "Rol", "Estado"]}
                  data={filteredUsers}
                  roles={roles}
                  onToggleState={toggleState}
                  onToggleRol={toggleRol}
                />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
