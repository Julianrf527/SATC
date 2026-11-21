import { RECURSOS_MATRIZ, type FilaRecursoAfectado, type RecursoMatriz } from "../types";

export const RECURSO_LABELS: Record<RecursoMatriz, string> = {
  AIRE: "Aire",
  SUELO: "Suelo",
  AGUA: "Agua",
  PAISAJE: "Paisaje",
  FLORA: "Flora",
  FAUNA: "Fauna",
  RUIDO: "Ruido",
  SOCIAL: "Social",
  OTRO: "Otro",
};

export const MAGNITUDES = ["LEVE", "MODERADO", "GRAVE"] as const;
export const REVERSIBILIDADES = ["REVERSIBLE", "IRREVERSIBLE"] as const;

export type Magnitud = FilaRecursoAfectado["magnitud"];
export type Reversibilidad = FilaRecursoAfectado["reversibilidad"];

// ── Matriz completa (la exige el backend en VISITA) ─────────────────────────

/** Las 9 filas, completando con "no existe" las que falten. */
export function matrizInicial(filas?: FilaRecursoAfectado[] | null): FilaRecursoAfectado[] {
  const porRecurso = new Map((filas ?? []).map((f) => [f.recurso, f]));
  return RECURSOS_MATRIZ.map(
    (recurso) => porRecurso.get(recurso) ?? { recurso, magnitud: null, reversibilidad: null, no_existe: true },
  );
}

/** Mensaje si a algún recurso con magnitud le falta la reversibilidad. */
export function errorMatriz(filas: FilaRecursoAfectado[]): string | null {
  const incompletas = filas.filter((f) => f.magnitud && !f.reversibilidad);
  return incompletas.length > 0
    ? `Falta la reversibilidad de: ${incompletas.map((f) => RECURSO_LABELS[f.recurso]).join(", ")}`
    : null;
}

/** Cuerpo para el backend: sin magnitud = "no existe". */
export function normalizarMatriz(filas: FilaRecursoAfectado[]): FilaRecursoAfectado[] {
  return filas.map((f) =>
    f.magnitud ? { ...f, no_existe: false } : { ...f, magnitud: null, reversibilidad: null, no_existe: true },
  );
}
