// Claves de react-query del módulo app-users. Jerárquicas: invalidar
// `usersKeys.all` refresca todo el módulo; `usersKeys.roles()` refresca los
// roles (incluido el listado con permisos, que cuelga de esa clave).
export const usersKeys = {
  all: ["app-users"] as const,
  roles: () => [...usersKeys.all, "roles"] as const,
  rolesConPermisos: () => [...usersKeys.roles(), "con-permisos"] as const,
  permisos: () => [...usersKeys.all, "permisos"] as const,
  usuarios: () => [...usersKeys.all, "usuarios"] as const,
  perfil: () => [...usersKeys.all, "perfil"] as const,
};
