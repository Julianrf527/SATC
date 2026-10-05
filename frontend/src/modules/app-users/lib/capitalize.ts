/** "  juan " → "Juan" (recorta y deja solo la inicial en mayúscula). */
export const capitalize = (text: string): string =>
  text.trim().charAt(0).toUpperCase() + text.trim().slice(1).toLowerCase();
