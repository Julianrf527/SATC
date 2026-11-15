// Fin de sesión por 401 (expirada o reemplazada) sin recargar la página.
//
// `apiCall` y las descargas viven fuera de React y no tienen `navigate`: la app
// registra aquí (dentro del Router) cómo ir al login y limpiar la caché de
// react-query. Si nada está registrado (p. ej. un test o antes de montar el
// Router), se recurre a la recarga completa de antes.
import { toastService } from "./toastService";

type IrAlLogin = () => void;

let irAlLogin: IrAlLogin | null = null;

const enLogin = () => window.location.pathname.startsWith("/login");

export const sesionService = {
  setHandler: (fn: IrAlLogin | null) => {
    irAlLogin = fn;
  },
  /**
   * Sesión inválida: avisa y lleva al login. Si ya se está en el login no hace
   * nada (credenciales malas o varias peticiones en vuelo que fallan a la vez:
   * solo la primera avisa y redirige).
   */
  cerrada: (mensaje: string) => {
    if (enLogin()) return;
    toastService.showToast({ id: Date.now(), message: mensaje, type: "error" });
    if (irAlLogin) irAlLogin();
    else window.location.href = "/login";
  },
};

export const MENSAJE_SESION_EXPIRADA = "Tu sesión ha expirado. Por favor, inicia sesión nuevamente.";
export const MENSAJE_SESION_REEMPLAZADA =
  "Tu sesión ha sido reemplazada por otro inicio de sesión. Si no fuiste tú, por favor cambia tu contraseña.";
