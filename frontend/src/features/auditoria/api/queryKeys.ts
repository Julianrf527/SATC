// Claves react-query de la feature auditoria.
export const auditoriaKeys = {
  all: ["auditoria"] as const,
  catalogo: (url: string) => [...auditoriaKeys.all, "catalogo", url] as const,
  etapas: (ids: number[]) => [...auditoriaKeys.all, "etapas", ...ids] as const,
};
