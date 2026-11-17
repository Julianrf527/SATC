import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ProcesoAdapter } from "./adapter";
import type {
  CambioProceso,
  DatosRevision,
  DatosVersion,
  ProcesoDetalle,
  ResultadoAccion,
} from "./types";

/**
 * Un detalle recién pedido (p. ej. precargado al pasar el mouse) se reutiliza
 * al abrir el modal sin volver a pedirlo. Tras cualquier acción se invalida.
 */
const DETALLE_STALE_MS = 15_000;

export type UseProcesoRevisionOpciones = {
  /**
   * Tras una mutación exitosa (ya invalidado el detalle). El módulo invalida
   * aquí sus propias listas/etapas o reacciona a campos propios del resultado.
   */
  onCambio?: (cambio: CambioProceso) => void;
};

/**
 * Hook headless del proceso de revisión: detalle + mutaciones. No pinta nada;
 * `ProcesoDetalleModal` lo usa, y un módulo puede usarlo para su propia UI.
 *
 *   const proceso = useProcesoRevision(docsAdapter, id, { onCambio: () => invalidarLista() });
 *   proceso.revisar.mutate({ accion: "aprobado", comentario: "", adjunto: null });
 */
export function useProcesoRevision<D extends ProcesoDetalle>(
  adapter: ProcesoAdapter<D>,
  id: number | null,
  { onCambio }: UseProcesoRevisionOpciones = {},
) {
  const queryClient = useQueryClient();
  const queryKey = adapter.queryKey(id ?? 0);

  const detalle = useQuery({
    queryKey,
    queryFn: () => adapter.detalle(id as number),
    enabled: id !== null,
    staleTime: DETALLE_STALE_MS,
  });

  // Sin `await`: el formulario se cierra apenas el servidor confirma y el
  // detalle se refresca en segundo plano (antes el botón seguía girando
  // durante el POST + la recarga del detalle).
  const alCambiar = (tipo: CambioProceso["tipo"]) => (resultado: ResultadoAccion) => {
    void queryClient.invalidateQueries({ queryKey });
    onCambio?.({ tipo, resultado });
  };

  const revisar = useMutation({
    mutationFn: (datos: DatosRevision) => adapter.revisar(id as number, datos),
    onSuccess: alCambiar("revision"),
  });

  const subirVersion = useMutation({
    mutationFn: (datos: DatosVersion) => adapter.subirVersion(id as number, datos),
    onSuccess: alCambiar("version"),
  });

  return {
    detalle: detalle.data,
    isPending: detalle.isPending,
    error: detalle.error,
    refetch: detalle.refetch,
    revisar,
    subirVersion,
  };
}

/**
 * Precarga el detalle de un proceso (al pasar el mouse o enfocar el botón que
 * lo abre) para que el modal abra ya con datos, sin spinner.
 *
 *   const precargar = usePrecargarProceso(docsAdapter);
 *   <button onMouseEnter={() => precargar(id)} onFocus={() => precargar(id)} />
 */
export function usePrecargarProceso<D extends ProcesoDetalle>(adapter: ProcesoAdapter<D>) {
  const queryClient = useQueryClient();
  return (id: number | null | undefined) => {
    if (id == null) return;
    void queryClient.prefetchQuery({
      queryKey: adapter.queryKey(id),
      queryFn: () => adapter.detalle(id),
      staleTime: DETALLE_STALE_MS,
    });
  };
}

export type ProcesoRevisionState<D extends ProcesoDetalle = ProcesoDetalle> = ReturnType<
  typeof useProcesoRevision<D>
>;
