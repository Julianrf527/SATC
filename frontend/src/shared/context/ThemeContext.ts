import { createContext } from "react";

/** Temas daisyUI usados por la app (ver app/index.css). */
export type Theme = "emerald" | "dark";

export const THEME_STORAGE_KEY = "theme";
export const DEFAULT_THEME: Theme = "emerald";

export type ThemeContextValue = {
  /** Tema activo, reactivo: los componentes se re-renderizan al cambiarlo. */
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  isDark: boolean;
};

export function readStoredTheme(): Theme {
  try {
    const saved = localStorage.getItem(THEME_STORAGE_KEY);
    return saved === "dark" || saved === "emerald" ? saved : DEFAULT_THEME;
  } catch {
    return DEFAULT_THEME;
  }
}

/**
 * El valor por defecto (sin provider) permite renderizar componentes sueltos
 * en Storybook/tests sin envolverlos; en la app real lo provee
 * `app/providers/ThemeProvider`.
 */
export const ThemeContext = createContext<ThemeContextValue>({
  theme: DEFAULT_THEME,
  setTheme: () => {},
  toggleTheme: () => {},
  isDark: false,
});
