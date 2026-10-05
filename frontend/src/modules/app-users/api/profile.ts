import { useMutation, useQuery } from "@tanstack/react-query";
import { apiRequest, jsonBody, USERS_ENDPOINTS } from "@shared/lib/api";
import type { PerfilUsuario } from "../types";
import { usersKeys } from "./queryKeys";

type MeApi = {
  usuario?: Partial<Record<keyof PerfilUsuario, string | null>>;
};

/**
 * Datos personales del usuario autenticado (/auth/me). `gcTime: 0`: son datos
 * de la sesión y no deben sobrevivir en caché al salir de la pantalla.
 */
export function usePerfilQuery() {
  return useQuery({
    queryKey: usersKeys.perfil(),
    gcTime: 0,
    queryFn: async (): Promise<PerfilUsuario> => {
      const res = await apiRequest<MeApi>(USERS_ENDPOINTS.AUTH_ME);
      if (!res.usuario) throw new Error("Respuesta sin usuario");
      const u = res.usuario;
      return {
        primer_nombre: u.primer_nombre || "",
        segundo_nombre: u.segundo_nombre || "",
        primer_apellido: u.primer_apellido || "",
        segundo_apellido: u.segundo_apellido || "",
        correo: u.correo || "",
      };
    },
  });
}

export type ActualizarPerfilPayload = {
  first_name: string;
  middle_name: string;
  lastname: string;
  second_lastname: string;
  correo: string;
};

/** Sin invalidación: tras guardar, la pantalla cierra la sesión. */
export function useUpdatePerfilMutation() {
  return useMutation({
    mutationFn: (payload: ActualizarPerfilPayload) =>
      apiRequest(USERS_ENDPOINTS.USER_UPDATE, { method: "PUT", ...jsonBody(payload) }),
  });
}

export function useChangePasswordMutation() {
  return useMutation({
    mutationFn: (payload: { current_password: string; new_password: string }) =>
      apiRequest(USERS_ENDPOINTS.PASSWORD_CHANGE, { method: "POST", ...jsonBody(payload) }),
  });
}

/** Cierra la sesión en el servidor; nunca rechaza (el llamador redirige igual). */
export async function logout(): Promise<void> {
  try {
    await apiRequest(USERS_ENDPOINTS.AUTH_LOGOUT, { method: "POST" });
  } catch {
    // Se redirige al login independientemente del resultado.
  }
}
