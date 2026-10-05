import { useContext } from "react";
import { ThemeContext, type ThemeContextValue } from "@shared/context/ThemeContext";

/**
 * Tema daisyUI activo ("emerald" | "dark"), reactivo.
 *
 * Reemplaza el patrón `MutationObserver` sobre `[data-theme]`: un modal que
 * se monta con `createPortal` en `document.body` queda fuera del `<div
 * data-theme>` raíz, así que debe re-aplicar el tema:
 *
 *   const { theme } = useTheme();
 *   return createPortal(<div data-theme={theme}>...</div>, document.body);
 *
 * (El componente `Modal` de `@shared/ui` ya lo hace por ti.)
 */
export function useTheme(): ThemeContextValue {
  return useContext(ThemeContext);
}
