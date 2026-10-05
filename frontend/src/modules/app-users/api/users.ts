import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, jsonBody, USERS_ENDPOINTS } from "@shared/lib/api";
import type { ActualizarUsuarioPayload, UsuarioFila } from "../types";
import { usersKeys } from "./queryKeys";

/** Forma cruda de cada usuario en /user/all. */
type UsuarioApi = {
  id: number;
  numero_documento: number;
  primer_nombre: string;
  segundo_nombre: string | null;
  primer_apellido: string;
  segundo_apellido: string | null;
  correo: string;
  rol_id: number;
  state?: boolean;
};

export const nombreCompleto = (...partes: Array<string | null | undefined>) =>
  partes.filter(Boolean).join(" ");

const aFila = (u: UsuarioApi): UsuarioFila => ({
  id: u.id,
  document: u.numero_documento,
  name: nombreCompleto(u.primer_nombre, u.segundo_nombre, u.primer_apellido, u.segundo_apellido),
  email: u.correo,
  rol_id: u.rol_id,
  state: u.state ?? false,
  primer_nombre: u.primer_nombre,
  segundo_nombre: u.segundo_nombre,
  primer_apellido: u.primer_apellido,
  segundo_apellido: u.segundo_apellido,
});

/** Usuarios gestionables (/user/all), ya normalizados para la tabla. */
export function useUsersQuery() {
  return useQuery({
    queryKey: usersKeys.usuarios(),
    queryFn: async () => {
      const res = await apiRequest<{ data?: UsuarioApi[] }>(USERS_ENDPOINTS.USERS);
      return (res.data ?? []).map(aFila);
    },
  });
}

export type RegistrarUsuarioPayload = {
  first_name: string;
  middle_name: string;
  lastname: string;
  second_lastname: string;
  document: number;
  email: string;
  rol: number;
};

export function useRegisterUserMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: RegistrarUsuarioPayload) =>
      apiRequest(USERS_ENDPOINTS.USER_REGISTER, { method: "POST", ...jsonBody(payload) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: usersKeys.usuarios() }),
  });
}

export function useUpdateUserMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ActualizarUsuarioPayload }) =>
      apiRequest(USERS_ENDPOINTS.USER_ADMIN_UPDATE(id), { method: "PATCH", ...jsonBody(data) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: usersKeys.usuarios() }),
  });
}

/** Reenvía una contraseña temporal. `email_sent` indica si el correo salió. */
export function useResendPasswordMutation() {
  return useMutation({
    mutationFn: (id: number) =>
      apiRequest<{ email_sent?: boolean }>(USERS_ENDPOINTS.USER_RESEND_PASSWORD(id), {
        method: "POST",
      }),
  });
}
