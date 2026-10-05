import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, DOCUMENTS_ENDPOINTS } from "@shared/lib/api";
import type {
  CrearDocumentoDatos,
  EstadisticasDocumentos,
  FiltrosDocumentos,
  ListaDocumentos,
  RevisorDisponible,
} from "../types";
import { documentosKeys } from "./queryKeys";

export const PAGE_SIZE = 20;

/** Página de /docs/list con los filtros del servidor (estado y fechas). */
export function useDocumentosQuery(filtros: FiltrosDocumentos, page: number) {
  return useQuery({
    queryKey: documentosKeys.lista(filtros, page),
    placeholderData: keepPreviousData,
    queryFn: async (): Promise<ListaDocumentos> => {
      const params = new URLSearchParams();
      if (filtros.estado) params.append("estado", filtros.estado);
      if (filtros.fechaDesde) params.append("fecha_desde", filtros.fechaDesde);
      if (filtros.fechaHasta) params.append("fecha_hasta", filtros.fechaHasta);
      params.append("page", String(page));
      params.append("page_size", String(PAGE_SIZE));
      const res = await apiRequest<Partial<ListaDocumentos>>(
        `${DOCUMENTS_ENDPOINTS.DOCS_LIST}?${params.toString()}`,
      );
      const documentos = res.documentos ?? [];
      return {
        documentos,
        estados: res.estados ?? [],
        total: res.total ?? documentos.length,
        total_pages: res.total_pages ?? 1,
        page: res.page ?? page,
        page_size: res.page_size ?? PAGE_SIZE,
      };
    },
  });
}

/** Estadísticas del usuario según sus permisos (creador / revisor). */
export function useEstadisticasQuery() {
  return useQuery({
    queryKey: documentosKeys.stats(),
    queryFn: async () =>
      (await apiRequest<{ stats?: EstadisticasDocumentos }>(DOCUMENTS_ENDPOINTS.DOCS_STATS)).stats ?? {},
  });
}

/** Usuarios con permiso de revisor (excluye al solicitante). */
export function useRevisoresQuery() {
  return useQuery({
    queryKey: documentosKeys.revisores(),
    queryFn: async () =>
      (await apiRequest<{ usuarios?: RevisorDisponible[] }>(DOCUMENTS_ENDPOINTS.DOCS_REVIEWERS)).usuarios ?? [],
  });
}

/** Crea el documento con su versión 1 y refresca listados y estadísticas. */
export function useCrearDocumentoMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (datos: CrearDocumentoDatos) => {
      const form = new FormData();
      form.append("nombre", datos.nombre.trim());
      if (datos.descripcion.trim()) form.append("descripcion", datos.descripcion.trim());
      form.append("tipo_archivo", datos.tipo_archivo);
      form.append("revisores_ids", JSON.stringify(datos.revisores_ids));
      form.append("archivo", datos.archivo);
      return apiRequest<{ documento_id: number; message?: string }>(DOCUMENTS_ENDPOINTS.DOCS_CREATE, {
        method: "POST",
        body: form,
      });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: documentosKeys.listas() }),
  });
}

/** Invalidador para `onCambio` del modal de proceso: listas + stats. */
export function useInvalidarDocumentos() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: documentosKeys.listas() });
}
