import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "@shared/lib/api";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Datos administrativos: cambian poco y no queremos ráfagas al cambiar de pestaña.
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      // Los 4xx (permisos, validación, sesión) no mejoran reintentando.
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
        return failureCount < 2;
      },
    },
    mutations: { retry: false },
  },
});
