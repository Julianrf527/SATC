import { useState, type ReactNode } from "react";
import { Filter, Search, X } from "lucide-react";
import { Modal } from "@shared/ui";
import CustomSelect from "@shared/ui/form/CustomSelect";
import type { ModeloGenerico, Municipio } from "@shared/types/common";
import { useVeredasMunicipioQuery } from "./api";
import type {
  ExpedienteBase,
  ExpedienteListSlots,
  ExpedientesAdapter,
  ExpedientesConfig,
  FiltroAvanzadoBase,
} from "./types";

type Props<T extends ExpedienteBase, F extends FiltroAvanzadoBase> = {
  isOpen: boolean;
  onClose: () => void;
  onApplyFilters: (filtros: F) => void;
  adapter: ExpedientesAdapter<T, F>;
  config: ExpedientesConfig<T, F>;
  municipioList: Municipio[];
  recursoAfectadoList: ModeloGenerico[];
  renderExtra?: ExpedienteListSlots<F>["renderFiltrosAvanzadosExtra"];
};

const esVacio = (v: unknown) =>
  v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0);

/** Quita claves vacías; `valor_exacto` siempre viaja. */
function limpiarFiltros<F extends FiltroAvanzadoBase>(filtros: F): F {
  const limpio: Record<string, unknown> = {};
  Object.entries(filtros).forEach(([k, v]) => {
    if (k === "valor_exacto" || !esVacio(v)) limpio[k] = v;
  });
  return limpio as F;
}

const contarActivos = (filtros: FiltroAvanzadoBase) =>
  Object.entries(filtros).filter(([k, v]) => k !== "valor_exacto" && !esVacio(v)).length;

const toggleId = (lista: number[] | undefined, id: number) => {
  const cur = lista || [];
  return cur.includes(id) ? cur.filter((v) => v !== id) : [...cur, id];
};

function Seccion({ titulo, children }: { titulo: ReactNode; children: ReactNode }) {
  return (
    <div>
      <p className="text-xs font-semibold text-base-content/60 uppercase tracking-wider mb-3">
        {titulo}
      </p>
      {children}
    </div>
  );
}

/** Modal de búsqueda en BD. Lo propio de cada módulo entra por config y `renderExtra`. */
export default function FiltroAvanzadoModal<T extends ExpedienteBase, F extends FiltroAvanzadoBase>({
  isOpen,
  onClose,
  onApplyFilters,
  adapter,
  config,
  municipioList,
  recursoAfectadoList,
  renderExtra,
}: Props<T, F>) {
  const [filtros, setFiltrosState] = useState<F>({ valor_exacto: false } as F);
  const setFiltros = (updater: (prev: F) => F) => setFiltrosState(updater);

  const { data: veredas = [], isFetching: loadingVeredas } = useVeredasMunicipioQuery(
    adapter,
    filtros.municipio_id,
  );

  const activos = contarActivos(filtros);

  const handleApply = () => {
    onApplyFilters(limpiarFiltros(filtros));
    onClose();
  };

  const camposTexto = config.camposTextoAvanzado;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      size="2xl"
      icon={<Filter size={18} />}
      title="Filtros Avanzados"
      subtitle={
        activos > 0
          ? `${activos} filtro${activos > 1 ? "s" : ""} activo${activos > 1 ? "s" : ""}`
          : "Búsqueda en base de datos"
      }
      bodyClassName="space-y-5"
      footer={
        <>
          <button
            onClick={() => setFiltrosState({ valor_exacto: false } as F)}
            className="btn btn-ghost btn-sm gap-1 mr-auto"
            disabled={activos === 0}
          >
            <X className="w-3.5 h-3.5" />
            Limpiar
          </button>
          <button onClick={onClose} className="btn btn-ghost btn-sm">
            Cancelar
          </button>
          <button onClick={handleApply} className="btn btn-success btn-sm text-white gap-1.5">
            <Search className="w-3.5 h-3.5" />
            Buscar
            {activos > 0 && (
              <span className="badge badge-sm bg-white/20 text-white border-0">{activos}</span>
            )}
          </button>
        </>
      }
    >
      <Seccion titulo="Información del expediente">
        <div className={camposTexto.length > 1 ? "grid grid-cols-1 sm:grid-cols-2 gap-3" : ""}>
          {camposTexto.map((c) => (
            <div key={c.clave} className="flex flex-col">
              <label className="label py-1">
                <span className="text-base-content text-sm">{c.etiqueta}</span>
              </label>
              <input
                type="text"
                className="input input-sm"
                placeholder={c.placeholder}
                value={(filtros[c.clave] as string | undefined) || ""}
                onChange={(e) => setFiltros((p) => ({ ...p, [c.clave]: e.target.value }))}
              />
            </div>
          ))}
        </div>
      </Seccion>

      <div className="divider my-0" />

      <Seccion titulo="Ubicación">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="flex flex-col">
            <label className="label py-1">
              <span className="text-base-content text-sm">Municipio</span>
            </label>
            <CustomSelect
              className="select-sm"
              value={filtros.municipio_id || 0}
              onChange={(v) =>
                setFiltros((p) => {
                  if (v) return { ...p, municipio_id: v, vereda_ids: [] };
                  const n = { ...p };
                  delete n.municipio_id;
                  delete n.vereda_ids;
                  return n;
                })
              }
              placeholder="Todos los municipios"
              options={municipioList.map((m) => ({ value: m.id, label: m.nombre }))}
            />
          </div>

          {!!filtros.municipio_id && (
            <div className="flex flex-col">
              <label className="label py-1">
                <span className="text-base-content text-sm flex items-center gap-1">
                  Veredas
                  {loadingVeredas && <span className="loading loading-spinner loading-xs" />}
                  {(filtros.vereda_ids?.length ?? 0) > 0 && (
                    <span className="badge badge-success badge-xs">{filtros.vereda_ids!.length}</span>
                  )}
                </span>
              </label>
              <div className="border border-base-300 rounded-lg max-h-32 overflow-y-auto bg-base-50">
                {loadingVeredas ? (
                  <div className="flex justify-center py-4">
                    <span className="loading loading-spinner loading-sm" />
                  </div>
                ) : veredas.length === 0 ? (
                  <p className="text-xs text-base-content/60 text-center py-4">Sin veredas</p>
                ) : (
                  veredas.map((v) => (
                    <label
                      key={v.id}
                      className="flex items-center gap-2 cursor-pointer hover:bg-base-200 px-3 py-1.5"
                    >
                      <input
                        type="checkbox"
                        className="checkbox checkbox-success checkbox-xs"
                        checked={filtros.vereda_ids?.includes(v.id) || false}
                        onChange={() =>
                          setFiltros((p) => ({ ...p, vereda_ids: toggleId(p.vereda_ids, v.id) }))
                        }
                      />
                      <span className="text-xs">{v.nombre}</span>
                    </label>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </Seccion>

      <div className="divider my-0" />

      <Seccion
        titulo={
          <>
            Recursos afectados
            {(filtros.recurso_ids?.length ?? 0) > 0 && (
              <span className="badge badge-success badge-xs ml-2">{filtros.recurso_ids!.length}</span>
            )}
          </>
        }
      >
        <div className="border border-base-300 rounded-lg max-h-32 overflow-y-auto">
          {recursoAfectadoList.map((r) => (
            <label
              key={r.id}
              className="flex items-center gap-2 cursor-pointer hover:bg-base-200 px-3 py-1.5"
            >
              <input
                type="checkbox"
                className="checkbox checkbox-success checkbox-xs"
                checked={filtros.recurso_ids?.includes(r.id) || false}
                onChange={() =>
                  setFiltros((p) => ({ ...p, recurso_ids: toggleId(p.recurso_ids, r.id) }))
                }
              />
              <span className="text-sm">{r.nombre}</span>
            </label>
          ))}
        </div>
      </Seccion>

      {renderExtra && (
        <>
          <div className="divider my-0" />
          {renderExtra({ filtros, setFiltros })}
        </>
      )}

      <div className="divider my-0" />

      <label className="flex items-center gap-3 cursor-pointer">
        <input
          type="checkbox"
          className="checkbox checkbox-success checkbox-sm"
          checked={filtros.valor_exacto}
          onChange={(e) => setFiltros((p) => ({ ...p, valor_exacto: e.target.checked }))}
        />
        <div>
          <span className="text-sm font-medium text-base-content">Búsqueda exacta</span>
          <p className="text-xs text-base-content/60">Coincidencias exactas en lugar de parciales</p>
        </div>
      </label>
    </Modal>
  );
}
