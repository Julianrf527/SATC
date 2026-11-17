import type { FilaRecursoAfectado, RecursoMatriz } from "../types";

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
