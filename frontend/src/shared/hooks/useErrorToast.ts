import { useEffect, useRef } from "react";
import { getErrorMessage } from "@shared/lib/api";
import type { Toast } from "@shared/lib/toastService";

/**
 * Muestra un toast de error cada vez que `error` pasa a un valor nuevo (p. ej.
 * el `error` de un `useQuery`). `setToast` se guarda en un ref para que un
 * callback inline del padre no vuelva a disparar el toast.
 *
 *   const municipios = useMunicipiosQuery();
 *   useErrorToast(municipios.error, setToast, "Error al cargar los municipios");
 */
export function useErrorToast(
  error: unknown,
  setToast: (toast: Toast) => void,
  fallback: string,
): void {
  const setToastRef = useRef(setToast);
  const fallbackRef = useRef(fallback);
  useEffect(() => {
    setToastRef.current = setToast;
    fallbackRef.current = fallback;
  }, [setToast, fallback]);

  useEffect(() => {
    if (!error) return;
    setToastRef.current({
      id: Date.now(),
      message: getErrorMessage(error, fallbackRef.current),
      type: "error",
    });
  }, [error]);
}
