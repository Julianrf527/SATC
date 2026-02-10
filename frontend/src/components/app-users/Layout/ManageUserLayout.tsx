import { useEffect, useMemo, useState } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import TitleForm from "../../Label/TitleForm";
import TableUsers from "../../app-users/Table/TableUsers";

type User = {
  id: number;
  name: string;
  email: string;
  rol_id: number;
  state: boolean;
};

type Role = { id: number; name: string };

type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function ManageUserLayout({ setToast }: Props) {
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);

  // Filtros
  const [documentFilter, setDocumentFilter] = useState("");
  const [nameFilter, setNameFilter] = useState("");
  const [emailFilter, setEmailFilter] = useState("");
  const [stateFilter, setStateFilter] = useState("all");
  const [roleFilter, setRoleFilter] = useState("all");

  // Función para construir nombre completo
  const buildFullName = (
    primerNombre: string,
    segundoNombre: string | null,
    primerApellido: string,
    segundoApellido: string | null
  ): string => {
    const partes = [
      primerNombre,
      segundoNombre,
      primerApellido,
      segundoApellido,
    ].filter(Boolean);
    return partes.join(" ");
  };

  // Carga inicial
  useEffect(() => {
    async function loadUsers() {
      try {
        const res = await apiCall(API_CONFIG.ENDPOINTS.USERS, {
          method: "GET",
        });

        if (!res.ok) {
          setToast({
            id: Date.now(),
            message: res.msg || "Error al cargar los usuarios",
            type: "error",
          });
        } else {
          const mapped: User[] = (res.data || []).map((u: any) => ({
            id: u.id,
            name: buildFullName(
              u.primer_nombre,
              u.segundo_nombre,
              u.primer_apellido,
              u.segundo_apellido
            ),
            email: u.correo,
            rol_id: u.rol_id,
            state: typeof u.state !== "undefined" ? u.state : false,
          }));
          setUsers(mapped);
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

        if (res.ok) {
          setRoles(res.data || []);
        } else {
          setToast({
            id: Date.now(),
            message: res.msg || "Error al cargar los roles",
            type: "error",
          });
        }
      } catch {
        setToast({
          id: Date.now(),
          message: "Error al cargar los roles",
          type: "error",
        });
      }
    }

    loadUsers();
    loadRoles();
  }, []);

  // Filtrado instantáneo
  const filteredUsers = useMemo(() => {
    const doc = documentFilter.trim();
    const name = nameFilter.trim().toLowerCase();
    const email = emailFilter.trim().toLowerCase();

    return users.filter((u) => {
      const matchesDoc = doc ? String(u.id).includes(doc) : true;
      const matchesName = name ? u.name.toLowerCase().includes(name) : true;
      const matchesEmail = email ? u.email.toLowerCase().includes(email) : true;
      const matchesState =
        stateFilter === "all"
          ? true
          : stateFilter === "active"
          ? u.state === true
          : u.state === false;
      const matchesRole =
        roleFilter === "all" ? true : u.rol_id === Number(roleFilter);

      return (
        matchesDoc && matchesName && matchesEmail && matchesState && matchesRole
      );
    });
  }, [users, documentFilter, nameFilter, emailFilter, stateFilter, roleFilter]);

  // Cambiar estado
  const toggleState = async (id: number) => {
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.USER_TOGGLE_STATE(id), {
        method: "PATCH",
      });

      if (res.ok) {
        setUsers((prev) =>
          prev.map((u) => (u.id === id ? { ...u, state: !u.state } : u))
        );
        setToast({
          id: Date.now(),
          message: res.msg || "El usuario se actualizó correctamente",
          type: "success",
        });
      } else {
        setToast({
          id: Date.now(),
          message: res.msg || "No se pudo actualizar el estado",
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

  // Cambiar rol
  const toggleRol = async (id: number, newRol: number) => {
    try {
      const res = await apiCall(
        API_CONFIG.ENDPOINTS.USER_TOGGLE_ROLE(id, newRol),
        {
          method: "PATCH",
        }
      );

      if (res.ok) {
        setUsers((prev) =>
          prev.map((u) => (u.id === id ? { ...u, rol_id: newRol } : u))
        );
        setToast({
          id: Date.now(),
          message: res.msg || "El usuario se actualizó correctamente",
          type: "success",
        });
      } else {
        setToast({
          id: Date.now(),
          message: res.msg || "No se pudo actualizar el rol",
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

  return (
    <div className="bg-base-200">
      <section className="w-full h-full flex justify-center items-start min-h-[calc(100vh-4rem)] overflow-hidden p-4">
        <div className="w-full max-w-6xl h-full">
          <div className="card bg-base-100 shadow-xl border border-base-300 w-full h-full">
            <div className="card-body px-6 py-6 flex flex-col h-full overflow-hidden">
              <TitleForm
                title="Gestionar Usuarios"
                body="Filtra y gestiona roles y estados de usuarios."
              />
              <TableUsers
                titles={["Cédula", "Nombre", "Correo", "Rol", "Estado"]}
                data={filteredUsers}
                onToggleState={toggleState}
                onToggleRol={toggleRol}
                roles={roles}
                docFilter={documentFilter}
                nameFilter={nameFilter}
                emailFilter={emailFilter}
                roleFilter={roleFilter}
                stateFilter={stateFilter}
                onDocFilterChange={setDocumentFilter}
                onNameFilterChange={setNameFilter}
                onEmailFilterChange={setEmailFilter}
                onRoleFilterChange={setRoleFilter}
                onStateFilterChange={setStateFilter}
              />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
