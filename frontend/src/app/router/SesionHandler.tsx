import { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { sesionService } from "@shared/lib/sesionService";
import { queryClient } from "../providers/queryClient";

/**
 * Registra en `sesionService` cómo terminar la sesión tras un 401: navegación
 * SPA al login (sin recarga) y, ya en el login, `queryClient.clear()` para no
 * dejar datos del usuario anterior en caché. Se limpia DESPUÉS de navegar para
 * que las pantallas aún montadas no vuelvan a pedir sus datos (y a recibir 401).
 */
export default function SesionHandler() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const limpiarPendiente = useRef(false);

  useEffect(() => {
    sesionService.setHandler(() => {
      limpiarPendiente.current = true;
      navigate("/login", { replace: true });
    });
    return () => sesionService.setHandler(null);
  }, [navigate]);

  useEffect(() => {
    if (limpiarPendiente.current && pathname.startsWith("/login")) {
      limpiarPendiente.current = false;
      queryClient.clear();
    }
  }, [pathname]);

  return null;
}
