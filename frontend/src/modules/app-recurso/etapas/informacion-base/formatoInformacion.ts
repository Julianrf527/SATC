/** Palabras que van en minúscula dentro de un nombre ("Ojo de Agua"). */
const MENORES = new Set(["de", "del", "la", "las", "el", "los", "y", "e"]);

/** "QUEBRADA LA ROSA" → "Quebrada la Rosa" (catálogos y nombres vienen en mayúsculas). */
export function capitalizar(texto: string | null | undefined): string {
  if (!texto) return "";
  return texto
    .trim()
    .toLowerCase()
    .split(/\s+/)
    .map((p, i) => (i > 0 && MENORES.has(p) ? p : p.charAt(0).toUpperCase() + p.slice(1)))
    .join(" ");
}

/**
 * Fuente en una sola línea: clase(s) y nombre propio.
 * ["QUEBRADA"], "SAN ANTONIO" → "Quebrada, San Antonio";
 * ["QUEBRADA", "NACIMIENTO"], "EL ALIZAL" → "Quebrada y Nacimiento, El Alizal".
 */
export function textoFuente(clases: string[], nombre: string | null | undefined): string {
  const tipos = clases.map(capitalizar).filter(Boolean);
  const clase =
    tipos.length > 1 ? `${tipos.slice(0, -1).join(", ")} y ${tipos[tipos.length - 1]}` : (tipos[0] ?? "");
  const propio = capitalizar(nombre);
  return [clase, propio].filter(Boolean).join(", ");
}
