import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, jsonBody, USERS_ENDPOINTS } from "@shared/lib/api";
import type { Rol, RolResumen } from "../types";
import { usersKeys } from "./queryKeys";

/**
 * Roles asignables por el usuario autenticado. El endpoint /role/all ya filtra
 * los roles cuyos permisos son subconjunto de los del usuario.
 *
 * Al compartir `queryKey`, todos los componentes que lo usen comparten caché
 * y una sola petición en vuelo.
 */
export function useRolesQuery() {
  return useQuery({
    queryKey: usersKeys.roles(),
    queryFn: async () => {
      const res = await apiRequest<{ data?: RolResumen[] }>(USERS_ENDPOINTS.ROL_LIST);
      return res.data ?? [];
    },
  });
}

/** Roles con sus ids de permisos (/role/role-permissions), para el editor de roles. */
export function useRolesConPermisosQuery() {
  return useQuery({
    queryKey: usersKeys.rolesConPermisos(),
    queryFn: async () => {
      const res = await apiRequest<{ data?: Rol[] }>(USERS_ENDPOINTS.ROL_PERMISSIONS);
      return res.data ?? [];
    },
  });
}

export type GuardarRolVars = {
  /** Sin id = crear; con id = actualizar. */
  id?: number | string;
  nombre: string;
  permisos: number[];
};

/** Crea o actualiza un rol. Invalida `roles()` (listado simple y con permisos). */
export function useSaveRolMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, nombre, permisos }: GuardarRolVars) =>
      apiRequest(id ? USERS_ENDPOINTS.ROL_UPDATE(id) : USERS_ENDPOINTS.ROL_ADD, {
        method: id ? "PUT" : "POST",
        ...jsonBody({ nombre, permisos }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: usersKeys.roles() }),
  });
}

/**
 * Elimina un rol e invalida `roles()` para que todos los consumidores
 * (selectores y editor de roles) se refresquen solos.
 *
 *   const eliminar = useDeleteRolMutation();
 *   eliminar.mutate(rolId, { onSuccess: () => toast("Rol eliminado") });
 */
export function useDeleteRolMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (rolId: number | string) =>
      apiRequest(USERS_ENDPOINTS.ROL_DELETE(rolId), { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: usersKeys.roles() }),
  });
}
