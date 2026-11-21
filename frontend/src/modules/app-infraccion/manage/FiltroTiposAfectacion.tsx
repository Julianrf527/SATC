import { useEffect, useMemo } from "react";
import type { ModeloGenerico } from "@shared/types/common";
import type { FiltrosAvanzadosSlotContext } from "@features/expedientes";
import type { TipoAfectacion } from "../types";
import type { FiltroAvanzadoInfraccion } from "./expedientesAdapter";

type Props = FiltrosAvanzadosSlotContext<FiltroAvanzadoInfraccion> & {
  recursoAfectadoList: ModeloGenerico[];
  tipoAfectacionList: TipoAfectacion[];
};

/** Sección "Tipos de afectación" del modal de filtros avanzados (solo infracción). */
export default function FiltroTiposAfectacion({
  filtros,
  setFiltros,
  recursoAfectadoList,
  tipoAfectacionList,
}: Props) {
  const seleccionados = filtros.tipo_afectacion_ids ?? [];
  const recursoIds = filtros.recurso_ids;
  const recursos = useMemo(
    () => (recursoIds?.length ? recursoAfectadoList.filter((r) => recursoIds.includes(r.id)) : recursoAfectadoList),
    [recursoIds, recursoAfectadoList],
  );

  // Al acotar los recursos, los tipos de los recursos que ya no se muestran se
  // quitan de la selección: ocultos no se pueden desmarcar y se enviarían igual.
  const visibles = useMemo(() => {
    const ids = new Set(recursos.map((r) => r.id));
    return new Set(tipoAfectacionList.filter((t) => ids.has(t.recurso_id)).map((t) => t.id));
  }, [recursos, tipoAfectacionList]);
  const hayOcultos = seleccionados.some((id) => !visibles.has(id));
  useEffect(() => {
    if (!hayOcultos) return;
    setFiltros((p) => ({
      ...p,
      tipo_afectacion_ids: (p.tipo_afectacion_ids ?? []).filter((id) => visibles.has(id)),
    }));
  }, [hayOcultos, visibles, setFiltros]);

  const toggle = (id: number) =>
    setFiltros((p) => {
      const cur = p.tipo_afectacion_ids ?? [];
      return {
        ...p,
        tipo_afectacion_ids: cur.includes(id) ? cur.filter((v) => v !== id) : [...cur, id],
      };
    });

  return (
    <div>
      <p className="text-xs font-semibold text-base-content/60 uppercase tracking-wider mb-3">
        Tipos de afectación
        {seleccionados.length > 0 && (
          <span className="badge badge-success badge-xs ml-2">{seleccionados.length}</span>
        )}
      </p>
      <div className="border border-base-300 rounded-lg max-h-40 overflow-y-auto">
        {recursos.map((recurso) => {
          const tipos = tipoAfectacionList.filter((t) => t.recurso_id === recurso.id);
          if (tipos.length === 0) return null;
          return (
            <div key={recurso.id}>
              <p className="px-3 pt-2 pb-1 text-xs font-semibold text-base-content/60 uppercase tracking-wide">
                {recurso.nombre}
              </p>
              {tipos.map((t) => (
                <label
                  key={t.id}
                  className="flex items-center gap-2 cursor-pointer hover:bg-base-200 px-3 py-1.5"
                >
                  <input
                    type="checkbox"
                    className="checkbox checkbox-success checkbox-xs"
                    checked={seleccionados.includes(t.id)}
                    onChange={() => toggle(t.id)}
                  />
                  <span className="text-sm">{t.nombre}</span>
                </label>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
