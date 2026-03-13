import { apiCall, API_CONFIG } from "../../../utils/api";
import React from "react";
import Input from "../../Input/Input";

type Props = {
  permission: { id: number; name: string; menu_path: string }[];
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function NewRole({ permission, setToast }: Props) {
  const roleNameRef = React.useRef<HTMLInputElement>(null);
  const [permissionList, setPermissionList] = React.useState<number[]>([]);
  const [searchTerm, setSearchTerm] = React.useState("");
  const [currentPage, setCurrentPage] = React.useState(1);
  const itemsPerPage = 8;

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
  React.useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm]);

  const toggleAddRol = async () => {
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
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.ROL_ADD, {
        method: "POST",
        body: JSON.stringify({
          name: roleNameRef.current.value,
          permission: permissionList,
        }),
      });
      if (res.ok) {
        setToast({
          id: Date.now(),
          message: "Rol creado correctamente",
          type: "success",
        });
        if (roleNameRef.current) roleNameRef.current.value = "";
        setPermissionList([]);
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al crear el rol",
          type: "error",
        });
      }
    } catch (e) {
      /* console.error("Error al hacer fetch:", e); */
      setToast({
        id: Date.now(),
        message: "Error al crear el rol",
        type: "error",
      });
    }
  };

  return (
    <div className="card bg-base-100 shadow-md border border-base-300 h-full flex flex-col">
      <div className="card-body flex flex-col h-full">
        {/* Header - Altura fija */}
        <div className="flex items-center gap-3 mb-6 flex-shrink-0">
          <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
            <svg
              className="w-5 h-5 text-success"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8.8 4.354a4 4 0 1 0 0 8a4 4 0 1 0 0-8M15 23H3v-1a6 6 0 0 1 12 0v1zm0 0h6v-1a6 6 0 0 0-9-5.197m6-9a2.5 2.5 0 1 1-5 0a2.5 2.5 0 0 1 5 0z"
              />
            </svg>
          </div>
          <div>
            <h3 className="text-xl font-bold">Nuevo Rol</h3>
            <p className="text-sm text-base-content/60">
              Asigna permisos al nuevo rol
            </p>
          </div>
        </div>

        {/* Input del nombre del rol - Altura fija */}
        <div className="mb-4 flex-shrink-0">
          <Input placeholder="Nombre del Rol" inputRef={roleNameRef} />
        </div>

        {/* Barra de búsqueda y contador - Altura fija */}
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
            <div className="alert alert-info shadow-sm py-2">
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

        {/* Tabla de permisos - Espacio flexible */}
        <div className="overflow-hidden rounded-lg border border-base-300 mb-4 flex-1 min-h-0 flex flex-col">
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
                                ? "badge-success"
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
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
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

        {/* Botón de crear - Altura fija */}
        <div className="flex justify-end pt-4 border-t border-base-300 flex-shrink-0">
          <button
            onClick={toggleAddRol}
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
                d="M12 6v6m0 0v6m0-6h6m-6 0H6"
              />
            </svg>
            Crear Rol
          </button>
        </div>
      </div>
    </div>
  );
}
