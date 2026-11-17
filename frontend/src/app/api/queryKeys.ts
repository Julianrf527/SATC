// Claves de react-query de la capa app (sesión y shell). Jerárquicas:
// invalidar `appKeys.all` refresca todo lo de esta capa.
export const appKeys = {
  all: ["app"] as const,
  me: () => [...appKeys.all, "me"] as const,
};
