import { useCallback } from "react";
import { useEscrituraEtapaMutation, type EscrituraEtapa, type RespuestaEtapa } from "../../api/etapas";
import { mensajeEscritura } from "../../api/errors";
import type { SetToast } from "../../types";

type Opciones = {
  /** Toast de éxito si el backend no manda `message`. */
  exito: string;
  /** Toast de error si el backend no manda `detail`. */
  error: string;
  onSuccess?: (res: RespuestaEtapa) => void;
  /** Error ya traducido (para mostrarlo dentro de un modal en vez de un toast). */
  onError?: (mensaje: string) => void;
};

/**
 * Ejecuta una escritura de etapa con los toasts de siempre. Tras el éxito o
 * un 409 la mutación ya recargó el árbol de etapas.
 */
export function useEscritura(expedienteId: number, setToast: SetToast) {
  const mutation = useEscrituraEtapaMutation(expedienteId);
  const { mutate } = mutation;

  const ejecutar = useCallback(
    (escritura: EscrituraEtapa, op: Opciones) =>
      mutate(escritura, {
        onSuccess: (res) => {
          setToast({ id: Date.now(), message: res?.message || op.exito, type: "success" });
          op.onSuccess?.(res);
        },
        onError: (err) => {
          const mensaje = mensajeEscritura(err, op.error);
          if (op.onError) op.onError(mensaje);
          else setToast({ id: Date.now(), message: mensaje, type: "error" });
        },
      }),
    [mutate, setToast],
  );

  return { ejecutar, ocupado: mutation.isPending };
}
