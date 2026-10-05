import { useEffect, useMemo, useState } from "react";
import { Users } from "lucide-react";
import TableUsers from "../table/TableUsers";
import UserFilters from "../table/UserFilters";
import { FILTROS_VACIOS, type FiltrosUsuarios } from "../table/filtrosUsuarios";
import EditUserModal from "../modal/EditUserModal";
import ConfirmResendPasswordModal from "../modal/ConfirmResendPasswordModal";
import type { ActualizarUsuarioPayload, SetToast, UsuarioFila } from "../types";
import { useRolesQuery } from "../api/roles";
import {
  useResendPasswordMutation,
  useUpdateUserMutation,
  useUsersQuery,
} from "../api/users";
import { apiErrorMessage } from "../api/errors";

type Props = {
  setToast: SetToast;
};

export default function ManageUserLayout({ setToast }: Props) {
  const { data: users = [], isPending: loadingUsers, error: usersError } = useUsersQuery();
  // Sin roles la pantalla sigue siendo usable: su error no se notifica.
  const { data: rolList = [], isPending: loadingRoles } = useRolesQuery();
  const loading = loadingUsers || loadingRoles;
  const updateUser = useUpdateUserMutation();
  const resendPassword = useResendPasswordMutation();

  const [filtros, setFiltros] = useState<FiltrosUsuarios>(FILTROS_VACIOS);
  const [selectedUser, setSelectedUser] = useState<UsuarioFila | null>(null);
  const [resendTarget, setResendTarget] = useState<UsuarioFila | null>(null);

  useEffect(() => {
    if (!usersError) return;
    setToast({
      id: Date.now(),
      message: apiErrorMessage(usersError, "Error al cargar los usuarios"),
      type: "error",
    });
  }, [usersError, setToast]);

  const filteredUsers = useMemo(() => {
    const doc = filtros.documento.trim();
    const name = filtros.nombre.trim().toLowerCase();
    const email = filtros.correo.trim().toLowerCase();
    return users.filter((u) => {
      const matchesDoc = doc ? String(u.document).includes(doc) : true;
      const matchesName = name ? u.name.toLowerCase().includes(name) : true;
      const matchesEmail = email ? u.email.toLowerCase().includes(email) : true;
      const matchesState =
        filtros.estado === "all" ? true : filtros.estado === "active" ? u.state : !u.state;
      const matchesRole = filtros.rol === "all" ? true : u.rol_id === Number(filtros.rol);
      return matchesDoc && matchesName && matchesEmail && matchesState && matchesRole;
    });
  }, [users, filtros]);

  /** Rechaza si falla para que el modal de edición quede abierto con el error. */
  const handleSaveEdit = async (id: number, data: ActualizarUsuarioPayload) => {
    try {
      await updateUser.mutateAsync({ id, data });
      setToast({ id: Date.now(), message: "Usuario actualizado correctamente", type: "success" });
    } catch (e) {
      const message = apiErrorMessage(e, "No se pudo actualizar el usuario", "Error al actualizar el usuario");
      setToast({ id: Date.now(), message, type: "error" });
      throw new Error(message, { cause: e });
    }
  };

  const handleResendPassword = (id: number) => {
    resendPassword.mutate(id, {
      onSuccess: (res) =>
        setToast({
          id: Date.now(),
          message: res.email_sent
            ? "Contraseña reenviada correctamente"
            : "Contraseña actualizada, pero el envío del correo falló. Reintente el reenvío.",
          type: res.email_sent ? "success" : "error",
        }),
      onError: (e) =>
        setToast({
          id: Date.now(),
          message: apiErrorMessage(e, "No se pudo reenviar la contraseña"),
          type: "error",
        }),
    });
  };

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
                <p className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wider">
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
                  <p className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wider">
                    Total usuarios
                  </p>
                  <p className="text-lg font-bold text-primary leading-tight">
                    {users.length}
                    <span className="text-xs font-normal text-base-content/60 ml-1">
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
            <UserFilters
              value={filtros}
              onChange={setFiltros}
              onClear={() => setFiltros(FILTROS_VACIOS)}
              rolList={rolList}
            />

            {/* ── Card: Tabla ── */}
            <div className="card bg-base-100 shadow border border-base-300">
              <div className="card-body p-4">
                <TableUsers
                  titles={["Cédula", "Nombre", "Correo", "Rol", "Estado", "Acciones"]}
                  data={filteredUsers}
                  rolList={rolList}
                  onEdit={(u) => setSelectedUser(u)}
                  onResendPassword={(u) => setResendTarget(u)}
                />
              </div>
            </div>
          </>
        )}
        </div>
      </div>

      <EditUserModal
        user={selectedUser}
        rolList={rolList}
        onClose={() => setSelectedUser(null)}
        onSave={handleSaveEdit}
      />
      <ConfirmResendPasswordModal
        userName={resendTarget?.name ?? ""}
        isOpen={!!resendTarget}
        onClose={() => setResendTarget(null)}
        onConfirm={() => resendTarget && handleResendPassword(resendTarget.id)}
      />
    </>
  );
}
