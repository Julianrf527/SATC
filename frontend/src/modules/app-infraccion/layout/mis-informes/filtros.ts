import type { MiInforme } from "../../types";
import { claveEstado } from "../../informe-tecnico/estadoInforme";

export type FiltrosMisInformes = {
  radicado: string;
  tipo: string;
  rol: string;
  estado: string;
  soloMiTurno: boolean;
};

export const FILTROS_MIS_INFORMES: FiltrosMisInformes = {
  radicado: "",
  tipo: "all",
  rol: "all",
  estado: "all",
  soloMiTurno: false,
};

/** Filtro en cliente (/informes/mios devuelve todo lo del usuario). */
export function filtrarMisInformes(informes: MiInforme[], f: FiltrosMisInformes): MiInforme[] {
  const radicado = f.radicado.toLowerCase();
  return informes.filter(
    (inf) =>
      (!radicado || (inf.expediente_radicado ?? "").toLowerCase().includes(radicado)) &&
      (f.tipo === "all" || inf.tipo_informe === f.tipo) &&
      (f.rol === "all" || (f.rol === "profesional" ? inf.soy_profesional : inf.soy_revisor)) &&
      (f.estado === "all" || claveEstado(inf) === f.estado) &&
      (!f.soloMiTurno || inf.requiere_mi_accion),
  );
}
