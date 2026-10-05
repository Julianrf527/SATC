import type { Toast } from "@shared/lib/toastService";

/** Setter de toast que App.tsx inyecta a las pantallas del módulo. */
export type SetToast = (toast: Toast) => void;

export type Permiso = {
  id: number;
  nombre: string;
  menu_path: string;
};

export type Rol = {
    id: number;
    nombre: string;
    permisos: number[];
};

/** Lo mínimo que devuelve /users/role/all y usan los selectores de rol. */
export type RolResumen = Pick<Rol, "id" | "nombre">;

/** Fila de la tabla de gestión de usuarios (ya normalizada desde /user/all). */
export type UsuarioFila = {
  id: number;
  document: number;
  name: string;
  email: string;
  rol_id: number;
  state: boolean;
  primer_nombre: string;
  segundo_nombre: string | null;
  primer_apellido: string;
  segundo_apellido: string | null;
};

/** Payload de PATCH /user/{id} (edición por administrador). */
export type ActualizarUsuarioPayload = {
  document: number;
  first_name: string;
  middle_name: string;
  lastname: string;
  second_lastname: string;
  email: string;
  rol_id: number;
  activo: boolean;
};

/** Datos personales del usuario autenticado (/auth/me → usuario). */
export type PerfilUsuario = {
  primer_nombre: string;
  segundo_nombre: string;
  primer_apellido: string;
  segundo_apellido: string;
  correo: string;
};

/** Registro de auditoría de usuarios (/user/log). */
export type AuditoriaUsuario = {
  id: number;
  usuario_id: number;
  usuario_nombre: string;
  usuario_documento?: string | null;
  usuario_correo: string;
  tabla_afectada: string;
  tipo_operacion: string;
  descripcion: string;
  id_registro: string | null;
  fecha: string;
  datos_anteriores: Record<string, unknown>;
  datos_nuevos: Record<string, unknown>;
};

/** Estado del modal de confirmación de roles/permisos. */
export type TipoOperacion = "eliminar" | "crear" | "actualizar";
export type TipoCambio = "rol" | "permiso";
