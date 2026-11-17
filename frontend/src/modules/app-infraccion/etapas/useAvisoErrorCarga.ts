import { useEffect, useRef } from "react";
import { esErrorDeConexion } from "../api/errors";

type SetToast = (toast: { id: number; message: string; type: "success" | "error" }) => void;

/**
 * Muestra un toast cuando falla la carga de una query (una vez por error).
 * Conserva los dos mensajes que tenían las etapas: error HTTP vs. de conexión.
 */
export function useAvisoErrorCarga(
  error: unknown,
  setToast: SetToast,
  mensajes: { http: string; conexion: string },
) {
  const ultimo = useRef<unknown>(null);
  const { http, conexion } = mensajes;

  useEffect(() => {
    if (!error || error === ultimo.current) return;
    ultimo.current = error;
    setToast({ id: Date.now(), message: esErrorDeConexion(error) ? conexion : http, type: "error" });
  }, [error, setToast, http, conexion]);
}
