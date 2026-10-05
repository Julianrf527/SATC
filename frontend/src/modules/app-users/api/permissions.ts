import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, jsonBody, USERS_ENDPOINTS } from "@shared/lib/api";
import type { Permiso } from "../types";
import { usersKeys } from "./queryKeys";

/** Catálogo completo de permisos (/role/permissions). */
export function usePermissionsQuery() {
  return useQuery({
    queryKey: usersKeys.permisos(),
    queryFn: async () => {
      const res = await apiRequest<{ data?: Permiso[] }>(USERS_ENDPOINTS.PERMISSIONS);
      return res.data ?? [];
    },
  });
}

/**
 * Tras cambiar el catálogo de permisos también se invalidan los roles: un
 * permiso eliminado desaparece de los roles que lo tenían.
 */
function useInvalidarPermisos() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: usersKeys.permisos() }),
      queryClient.invalidateQueries({ queryKey: usersKeys.roles() }),
    ]);
}

export type GuardarPermisoVars = {
  /** Sin id = crear; con id = actualizar. */
  id?: string;
  name: string;
  menu_path: string;
};

export function useSavePermissionMutation() {
  const invalidar = useInvalidarPermisos();
  return useMutation({
    mutationFn: ({ id, name, menu_path }: GuardarPermisoVars) =>
      apiRequest(
        id ? USERS_ENDPOINTS.PERMISSION_UPDATE(id) : USERS_ENDPOINTS.PERMISSION_ADD,
        { method: id ? "PUT" : "POST", ...jsonBody({ name, menu_path }) },
      ),
    onSuccess: invalidar,
  });
}

export function useDeletePermissionMutation() {
  const invalidar = useInvalidarPermisos();
  return useMutation({
    mutationFn: (id: string) =>
      apiRequest(USERS_ENDPOINTS.PERMISSION_DELETE(id), { method: "DELETE" }),
    onSuccess: invalidar,
  });
}
