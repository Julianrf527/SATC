import { useEffect, useMemo, useState } from "react";
import { Users } from "lucide-react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import TableUsers from "../../app-users/Table/TableUsers";
import CustomSelect from "../../Common/Form/CustomSelect";

type User = {
  id: number;
  document: number;
  name: string;
  email: string;
  rol_id: number;
  state: boolean;
};

type Rol = { id: number; nombre: string };

type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function ManageUserLayout({ setToast }: Props) {
  const [users, setUsers] = useState<User[]>([]);
  const [rolList, setRolList] = useState<Rol[]>([]);
  const [loading, setLoading] = useState(true);

  const [documentFilter, setDocumentFilter] = useState("");
  const [nameFilter, setNameFilter] = useState("");
  const [emailFilter, setEmailFilter] = useState("");
  const [stateFilter, setStateFilter] = useState("all");
  const [roleFilter, setRoleFilter] = useState("all");

  const buildFullName = (
    a: string,
    b: string | null,
    c: string,
    d: string | null,
  ) => [a, b, c, d].filter(Boolean).join(" ");

  useEffect(() => {
    async function loadUsers() {
      try {
        const res = await apiCall(API_CONFIG.ENDPOINTS.USERS, {
          method: "GET",
        });
        if (!res.ok) {
          setToast({
            id: Date.now(),
            message: res.detail || res.msg || "Error al cargar los usuarios",
            type: "error",
          });
        } else {
          setUsers(
            (res.data || []).map((u: any) => ({
              id: u.id,
              document: u.numero_documento,
              name: buildFullName(
                u.primer_nombre,
                u.segundo_nombre,
                u.primer_apellido,
                u.segundo_apellido,
              ),
              email: u.correo,
              rol_id: u.rol_id,
              state: typeof u.state !== "undefined" ? u.state : false,
            })),
          );
        }
      } catch {
        setToast({
          id: Date.now(),
          message: "Error al cargar los usuarios",
          type: "error",
        });
      }
    }
    async function loadRoles() {
      try {
        const res = await apiCall(API_CONFIG.ENDPOINTS.ROL_LIST, {
          method: "GET",
        });
        if (res.ok) setRolList(res.data || []);
      } catch {
        // Sin roles la pantalla sigue siendo usable: no se interrumpe la carga.
      }
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
      const matchesState =
        stateFilter === "all"
          ? true
          : stateFilter === "active"
            ? u.state
            : !u.state;
      const matchesRole =
        roleFilter === "all" ? true : u.rol_id === Number(roleFilter);
      return (
        matchesDoc && matchesName && matchesEmail && matchesState && matchesRole
      );
    });
  }, [users, documentFilter, nameFilter, emailFilter, stateFilter, roleFilter]);

  const toggleState = async (id: number) => {
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.USER_TOGGLE_STATE(id), {
        method: "PATCH",
      });
      if (res.ok) {
        setUsers((prev) =>
          prev.map((u) => (u.id === id ? { ...u, state: !u.state } : u)),
        );
        setToast({
          id: Date.now(),
          message: "Estado actualizado correctamente",
          type: "success",
        });
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || res.msg || "No se pudo actualizar el estado",
          type: "error",
        });
      }
    } catch {
      setToast({
        id: Date.now(),
        message: "No se pudo actualizar el estado",
        type: "error",
      });
    }
  };

  const toggleRol = async (id: number, newRol: number) => {
    try {
      const res = await apiCall(
        API_CONFIG.ENDPOINTS.USER_TOGGLE_ROLE(id, newRol),
        { method: "PATCH" },
      );
      if (res.ok) {
        setUsers((prev) =>
          prev.map((u) => (u.id === id ? { ...u, rol_id: newRol } : u)),
        );
        setToast({
          id: Date.now(),
          message: res.msg || "Rol actualizado correctamente",
          type: "success",
        });
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || res.msg || "No se pudo actualizar el rol",
          type: "error",
        });
      }
    } catch {
      setToast({
        id: Date.now(),
        message: "No se pudo actualizar el rol",
        type: "error",
      });
    }
  };

  const clearFilters = () => {
    setDocumentFilter("");
    setNameFilter("");
    setEmailFilter("");
    setStateFilter("all");
    setRoleFilter("all");
  };

  const hasActiveFilters =
    documentFilter.trim() !== "" ||
    nameFilter.trim() !== "" ||
    emailFilter.trim() !== "" ||
    roleFilter !== "all" ||
    stateFilter !== "all";

  return (
    <>
      <div className="bg-gradient-to-r from-base-100 to-base-200/50 border-b border-base-300 shadow-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
                <Users className="text-primary" size={20} />
              </div>
              <div>
                <p className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wider">
                  Módulo de Usuarios
                </p>
                <h1 className="text-lg font-bold text-base-content">
                  Gestión de Usuarios
                </h1>
              </div>
            </div>
            {!loading && (
              <div className="flex items-center gap-3">
                <div className="text-right hidden sm:block">
                  <p className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wider">
                    Total usuarios
                  </p>
                  <p className="text-lg font-bold text-primary leading-tight">
                    {users.length}
                    <span className="text-xs font-normal text-base-content/50 ml-1">
                      ({filteredUsers.length} visibles)
                    </span>
                  </p>
                </div>
                <div className="w-px h-8 bg-base-300 hidden sm:block" />
                <div className="badge badge-primary badge-outline gap-1 hidden sm:flex">
                  <span className="text-xs font-semibold">
                    {users.filter((u) => u.state).length} activos
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="w-full min-h-[calc(100vh-4rem)] bg-gradient-to-br from-base-200 to-base-300 p-4">
        <div className="max-w-7xl mx-auto space-y-4">

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
                        d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L13 13.414V19a1 1 0 01-.553.894l-4 2A1 1 0 017 21v-7.586L3.293 6.707A1 1 0 013 6V4z"
                      />
                    </svg>
                    Filtros de búsqueda
                    {hasActiveFilters && (
                      <span className="badge badge-primary badge-sm">
                        activos
                      </span>
                    )}
                  </span>
                  <button
                    onClick={clearFilters}
                    disabled={!hasActiveFilters}
                    className={`btn btn-xs gap-1 ${hasActiveFilters ? "btn-error btn-outline" : "btn-ghost opacity-40"}`}
                  >
                    <svg
                      className="w-3 h-3"
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
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
                  <div className="form-control">
                    <label className="label py-1">
                      <span className="label-text text-xs">Cédula</span>
                    </label>
                    <input
                      type="text"
                      placeholder="Buscar..."
                      className="input input-sm input-bordered"
                      value={documentFilter}
                      onChange={(e) => setDocumentFilter(e.target.value)}
                    />
                  </div>
                  <div className="form-control">
                    <label className="label py-1">
                      <span className="label-text text-xs">Nombre</span>
                    </label>
                    <input
                      type="text"
                      placeholder="Buscar..."
                      className="input input-sm input-bordered"
                      value={nameFilter}
                      onChange={(e) => setNameFilter(e.target.value)}
                    />
                  </div>
                  <div className="form-control">
                    <label className="label py-1">
                      <span className="label-text text-xs">Correo</span>
                    </label>
                    <input
                      type="text"
                      placeholder="Buscar..."
                      className="input input-sm input-bordered"
                      value={emailFilter}
                      onChange={(e) => setEmailFilter(e.target.value)}
                    />
                  </div>
                  <div className="form-control">
                    <label className="label py-1">
                      <span className="label-text text-xs">Rol</span>
                    </label>
                    <CustomSelect
                      className="select-sm"
                      hidePlaceholderOption
                      value={roleFilter}
                      onChange={setRoleFilter}
                      options={[
                        { value: "all", label: "Todos" },
                        ...rolList.map((r) => ({ value: String(r.id), label: r.nombre })),
                      ]}
                    />
                  </div>
                  <div className="form-control">
                    <label className="label py-1">
                      <span className="label-text text-xs">Estado</span>
                    </label>
                    <CustomSelect
                      className="select-sm"
                      hidePlaceholderOption
                      value={stateFilter}
                      onChange={setStateFilter}
                      options={[
                        { value: "all", label: "Todos" },
                        { value: "active", label: "Activos" },
                        { value: "inactive", label: "Inactivos" },
                      ]}
                    />
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
                  rolList={rolList}
                  onToggleState={toggleState}
                  onToggleRol={toggleRol}
                />
              </div>
            </div>
          </>
        )}
        </div>
      </div>
    </>
  );
}
