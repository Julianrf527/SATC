import { useMemo, useState } from "react";
import { fechaLocalYMD } from "@shared/lib/format";
import type { ExpedienteBase, FiltroRapido, OpcionFiltro } from "./types";

const TODOS = "all";

export type FiltroRapidoVista = {
  id: string;
  valor: string;
  opciones: OpcionFiltro[];
};

/**
 * Estado y lógica de los filtros locales (sobre la lista ya cargada):
 * radicado, nombre/documento de involucrado, rango de fechas de creación y
 * los selects que define el módulo. `filtros` debe ser estable (constante
 * del módulo).
 */
export function useFiltrosRapidos<T extends ExpedienteBase>(lista: T[], filtros: FiltroRapido<T>[]) {
  const [radicado, setRadicado] = useState("");
  const [nombre, setNombre] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [selecciones, setSelecciones] = useState<Record<string, string>>({});

  const selects = useMemo<FiltroRapidoVista[]>(
    () =>
      filtros.map((f) => {
        let opciones: OpcionFiltro[];
        if (f.tipo === "fijo") {
          opciones = f.opciones;
        } else {
          const valores = new Set<string>();
          lista.forEach((e) => {
            const v = f.valor(e);
            if (v) valores.add(v);
          });
          // La opción elegida sigue visible aunque ya no esté en la lista
          // (p. ej. tras una búsqueda avanzada): si no, el select queda en
          // blanco y la lista vacía sin explicación.
          const sel = selecciones[f.id];
          if (sel && sel !== TODOS) valores.add(sel);
          const arr = Array.from(valores);
          if (f.ordenar) arr.sort();
          opciones = arr.map((v) => ({ value: v, label: v }));
        }
        return {
          id: f.id,
          valor: selecciones[f.id] ?? TODOS,
          opciones: [{ value: TODOS, label: f.etiquetaTodos }, ...opciones],
        };
      }),
    [lista, filtros, selecciones],
  );

  const filtrados = useMemo(() => {
    const radicadoLower = radicado.trim().toLowerCase();
    const nombreLower = nombre.trim().toLowerCase();
    const buscaDocumento = /^\d+$/.test(nombreLower);

    return lista.filter((e) => {
      if (radicadoLower && !(e.radicado ?? "").toLowerCase().includes(radicadoLower)) return false;

      if (nombreLower) {
        const involucrados = e.involucrados ?? [];
        const coincide = buscaDocumento
          ? involucrados.some((i) => String(i.numero_documento ?? "").includes(nombreLower))
          : involucrados.some((i) => (i.nombre ?? "").toLowerCase().includes(nombreLower));
        if (!coincide) return false;
      }

      // Día local de creación (el backend manda el timestamp en UTC); ambos
      // extremos incluidos.
      if (desde || hasta) {
        const dia = fechaLocalYMD(e.fecha_creacion);
        if (!dia) return false;
        if (desde && dia < desde) return false;
        if (hasta && dia > hasta) return false;
      }

      return filtros.every((f) => {
        const sel = selecciones[f.id] ?? TODOS;
        if (sel === TODOS) return true;
        return f.tipo === "fijo" ? f.coincide(e, sel) : f.valor(e) === sel;
      });
    });
  }, [lista, filtros, radicado, nombre, desde, hasta, selecciones]);

  const hayActivos =
    !!radicado ||
    !!nombre ||
    !!desde ||
    !!hasta ||
    Object.values(selecciones).some((v) => v !== TODOS);

  const limpiar = () => {
    setRadicado("");
    setNombre("");
    setDesde("");
    setHasta("");
    setSelecciones({});
  };

  const setSeleccion = (id: string, valor: string) =>
    setSelecciones((prev) => ({ ...prev, [id]: valor }));

  return {
    radicado,
    setRadicado,
    nombre,
    setNombre,
    desde,
    setDesde,
    hasta,
    setHasta,
    selects,
    setSeleccion,
    filtrados,
    hayActivos,
    limpiar,
  };
}

export type FiltrosRapidosState = ReturnType<typeof useFiltrosRapidos>;
