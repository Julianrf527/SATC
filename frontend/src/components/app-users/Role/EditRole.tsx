import Input from "../../Input/Input";
import { useEffect, useState, useRef } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import ConfirmDeleteRolePermissionModal from "./ConfirmDeleteRolePermissionModa";

type Roles = { id: number; name: string; permission: number[] };

type Props = {
  permission: { id: number; name: string; menu_path: string }[];
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function EditRol({ permission, setToast }: Props) {
  const roleNameRef = useRef<HTMLInputElement>(null);
  const [role, setRole] = useState<Roles[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState("0");
  const [permissionList, setPermissionList] = useState<number[]>([]);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 8;

  const handleRoleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const roleTemp = role.find((r) => r.id === Number(e.target.value));
    setPermissionList(roleTemp ? roleTemp.permission : []);
    setSelectedRoleId(e.target.value);
    roleNameRef.current!.value = roleTemp ? roleTemp.name : "";
  };

  const togglePermission = (id: number) => {
    setPermissionList((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id],
    );
  };

  // Filtrar permisos según búsqueda
  const filteredPermissions = permission.filter((p) =>
    p.name.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  // Calcular paginación
  const totalPages = Math.ceil(filteredPermissions.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentPermissions = filteredPermissions.slice(startIndex, endIndex);

  // Resetear página cuando cambia el término de búsqueda
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm]);

  const onEditRol = async () => {
    if (!roleNameRef.current || roleNameRef.current.value.trim() === "") {
      setToast({
        id: Date.now(),
        message: "El nombre del rol es obligatorio",
        type: "error",
      });
      return;
    }
    if (permissionList.length === 0) {
      setToast({
        id: Date.now(),
        message: "Debe seleccionar al menos un permiso",
        type: "error",
      });
      return;
    }
    if (selectedRoleId === "0" || selectedRoleId === "") {
      setToast({
        id: Date.now(),
        message: "Debe seleccionar un rol",
        type: "error",
      });
      return;
    }

    try {
      const res = await apiCall(
        API_CONFIG.ENDPOINTS.ROL_UPDATE(selectedRoleId),
        {
          method: "PUT",
          body: JSON.stringify({
            name: roleNameRef.current.value,
            permission: permissionList,
          }),
        },
      );
      if (res.ok) {
        setToast({
          id: Date.now(),
          message: "Rol actualizado correctamente",
          type: "success",
        });

        const updatedName = roleNameRef.current!.value;

        setRole((prev) =>
          prev.map((r) =>
            r.id === Number(selectedRoleId)
              ? {
                  ...r,
                  name: updatedName,
                  permission: permissionList,
                }
              : r,
          ),
        );

        setPermissionList([]);
        setSelectedRoleId("0");
        if (roleNameRef.current) roleNameRef.current.value = "";
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al actualizar el rol",
          type: "error",
        });
      }
    } catch (e) {
      /* console.error("Error al hacer fetch:", e); */
      setToast({
        id: Date.now(),
        message: "Error al actualizar el rol",
        type: "error",
      });
    }
  };

  const onDeleteRol = async () => {
    if (selectedRoleId === "0" || selectedRoleId === "") {
      setToast({
        id: Date.now(),
        message: "Debe seleccionar un rol",
        type: "error",
      });
      return;
    }

    setShowDeleteModal(true);
  };

  const handleConfirmDelete = async () => {
    setIsDeleting(true);

    try {
      const res = await apiCall(
        API_CONFIG.ENDPOINTS.ROL_DELETE(selectedRoleId),
        {
          method: "DELETE",
        },
      );

      if (res.ok) {
        setToast({
          id: Date.now(),
          message: "Rol eliminado correctamente",
          type: "success",
        });
        setRole((prev) => prev.filter((r) => r.id !== Number(selectedRoleId)));

        setPermissionList([]);
        setSelectedRoleId("0");
        if (roleNameRef.current) roleNameRef.current.value = "";
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al eliminar el rol",
          type: "error",
        });
      }
    } catch (e) {
      /* console.error("Error al hacer fetch:", e); */
      setToast({
        id: Date.now(),
        message: "Error al eliminar el rol",
        type: "error",
      });
    } finally {
      setIsDeleting(false);
      setShowDeleteModal(false);
    }
  };

  useEffect(() => {
    async function getRoles() {
      try {
        const res = await apiCall(API_CONFIG.ENDPOINTS.ROL_PERMISSIONS, {
          method: "GET",
        });
        if (res.ok) {
          setRole(res.data);
        } else {
          setToast({
            id: Date.now(),
            message: "Error al cargar los roles",
            type: "error",
          });
        }
      } catch (e) {
        /* console.error("Error al hacer fetch:", e); */
        setToast({
          id: Date.now(),
          message: "Error al cargar los permisos",
          type: "error",
        });
      }
    }
    getRoles();
  }, []);

  return (
    <div className="card bg-base-100 shadow-md border border-base-300 h-full flex flex-col">
      <ConfirmDeleteRolePermissionModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleConfirmDelete}
        type="rol"
        itemName={role.find((r) => r.id === Number(selectedRoleId))?.name}
        isDeleting={isDeleting}
      />

      <div className="card-body flex flex-col h-full">
        {/* Header - Altura fija */}
        <div className="flex items-center gap-3 mb-6 flex-shrink-0">
          <div className="w-10 h-10 bg-warning/10 rounded-lg flex items-center justify-center">
            <svg
              className="w-5 h-5 text-warning"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
              />
            </svg>
          </div>
          <div>
            <h3 className="text-xl font-bold">Editar Rol</h3>
            <p className="text-sm text-base-content/60">
              Modifica permisos de roles existentes
            </p>
          </div>
        </div>

        {/* Selector y Input - Altura fija */}
        <div className="mb-4 flex-shrink-0">
          <div className="form-control mb-4">
            <select
              className="select select-bordered w-full"
              onChange={handleRoleChange}
              value={selectedRoleId}
            >
              <option value="0">Seleccione un rol</option>
              {role.map((role) => (
                <option key={role.id} value={role.id}>
                  {role.name}
                </option>
              ))}
            </select>
          </div>

          {selectedRoleId !== "0" && (
            <div className="form-control">
              <Input placeholder="Nombre del Rol" inputRef={roleNameRef} />
            </div>
          )}
        </div>

        {/* Barra de búsqueda y contador - Altura fija */}
        {selectedRoleId !== "0" && (
          <div className="mb-4 flex-shrink-0 space-y-3">
            <div className="form-control">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Buscar permisos..."
                  className="input input-bordered w-full pl-10"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
                <svg
                  className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-base-content/50"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
              </div>
            </div>

            {/* Contador de permisos */}
            {permissionList.length > 0 && (
              <div className="alert alert-warning shadow-sm py-2">
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <span className="text-sm font-medium">
                  {permissionList.length} permiso
                  {permissionList.length !== 1 ? "s" : ""} seleccionado
                  {permissionList.length !== 1 ? "s" : ""}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Contenido dinámico - Espacio flexible */}
        <div className="flex-1 min-h-0 mb-4">
          {selectedRoleId !== "0" ? (
            <div className="overflow-hidden rounded-lg border border-base-300 h-full flex flex-col">
              <div className="overflow-y-auto flex-1">
                <table className="table table-zebra w-full">
                  <thead className="sticky top-0 bg-base-200 z-10">
                    <tr>
                      <th className="text-sm font-semibold">
                        <div className="flex items-center gap-2">
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
                              d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                            />
                          </svg>
                          Permiso
                        </div>
                      </th>
                      <th className="text-sm font-semibold w-32 text-center">
                        <div className="flex items-center justify-center gap-2">
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
                              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                            />
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                            />
                          </svg>
                          Acción
                        </div>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {currentPermissions.length > 0 ? (
                      currentPermissions.map((p) => (
                        <tr key={p.id} className="hover">
                          <td className="py-3">
                            <div className="flex items-start gap-2">
                              <span
                                className={`badge badge-sm mt-0.5 ${
                                  permissionList.includes(p.id)
                                    ? "badge-warning"
                                    : "badge-ghost"
                                }`}
                              >
                                {permissionList.includes(p.id) ? "✓" : "○"}
                              </span>
                              <span className="text-sm">{p.name}</span>
                            </div>
                          </td>
                          <td className="text-center">
                            <button
                              onClick={() => togglePermission(p.id)}
                              className={`btn btn-sm gap-2 ${
                                permissionList.includes(p.id)
                                  ? "btn-error btn-outline"
                                  : "btn-success text-white"
                              }`}
                            >
                              {permissionList.includes(p.id) ? (
                                <>
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
                                      d="M6 18L18 6M6 6l12 12"
                                    />
                                  </svg>
                                  Quitar
                                </>
                              ) : (
                                <>
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
                                      d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                                    />
                                  </svg>
                                  Agregar
                                </>
                              )}
                            </button>
                          </td>
                        </tr>
                      ))
                    ) : searchTerm ? (
                      <tr>
                        <td colSpan={2} className="text-center py-12">
                          <div className="flex flex-col items-center gap-3">
                            <svg
                              className="w-16 h-16 text-base-content/20"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                              />
                            </svg>
                            <div>
                              <p className="text-base-content/70 font-medium mb-1">
                                No se encontraron permisos
                              </p>
                              <p className="text-base-content/50 text-sm">
                                Intenta con otro término de búsqueda
                              </p>
                            </div>
                          </div>
                        </td>
                      </tr>
                    ) : (
                      <tr>
                        <td colSpan={2} className="text-center py-12">
                          <div className="flex flex-col items-center gap-3">
                            <svg
                              className="w-16 h-16 text-base-content/20"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                              />
                            </svg>
                            <p className="text-base-content/60 text-sm">
                              No hay permisos disponibles
                            </p>
                          </div>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Paginación */}
              {totalPages > 1 && (
                <div className="bg-base-100 border-t border-base-300 px-4 py-3 flex items-center justify-between flex-shrink-0">
                  <div className="text-sm text-base-content/60">
                    Mostrando {startIndex + 1}-
                    {Math.min(endIndex, filteredPermissions.length)} de{" "}
                    {filteredPermissions.length}
                  </div>
                  <div className="join">
                    <button
                      className="join-item btn btn-sm"
                      onClick={() =>
                        setCurrentPage(Math.max(1, currentPage - 1))
                      }
                      disabled={currentPage === 1}
                    >
                      «
                    </button>
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map(
                      (page) => (
                        <button
                          key={page}
                          className={`join-item btn btn-sm ${
                            currentPage === page ? "btn-active" : ""
                          }`}
                          onClick={() => setCurrentPage(page)}
                        >
                          {page}
                        </button>
                      ),
                    )}
                    <button
                      className="join-item btn btn-sm"
                      onClick={() =>
                        setCurrentPage(Math.min(totalPages, currentPage + 1))
                      }
                      disabled={currentPage === totalPages}
                    >
                      »
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-lg border border-base-300 h-full flex items-center justify-center">
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-base-200 rounded-full flex items-center justify-center mb-4 mx-auto">
                  <svg
                    className="w-8 h-8 text-warning"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                    />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-base-content/70 mb-2">
                  Selecciona un rol para editar
                </h3>
                <p className="text-sm text-base-content/60">
                  Elige un rol de la lista para modificar sus permisos
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Botones de acción - Altura fija */}
        <div className="flex-shrink-0">
          {selectedRoleId !== "0" && (
            <div className="flex gap-3 justify-end pt-4 border-t border-base-300">
              <button
                onClick={onDeleteRol}
                className="btn btn-error btn-outline gap-2"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
                Eliminar Rol
              </button>
              <button
                onClick={onEditRol}
                className="btn btn-success text-white gap-2"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                Actualizar Rol
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
