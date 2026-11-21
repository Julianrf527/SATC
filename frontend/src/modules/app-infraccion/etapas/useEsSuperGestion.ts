import { useAuth } from "@shared/context/AuthContext";

export const PERMISO_SUPER_GESTION = "infraccion_super_gestion";

/** ¿El usuario tiene super gestión de infracciones (cargue directo)? */
export function useEsSuperGestion(): boolean {
  const { user } = useAuth();
  return (user?.permisos ?? []).some((p) => p.name === PERMISO_SUPER_GESTION);
}
