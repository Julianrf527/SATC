import { useState, type ReactNode } from "react";
import { CalendarPlus, FileText, MapPin, Search } from "lucide-react";
import { formatDate } from "@shared/lib/format";
import type { ModeloGenerico, Municipio } from "@shared/types/common";
import ExpedienteCard from "./ExpedienteCard";
import FiltroAvanzadoModal from "./FiltroAvanzadoModal";
import FiltrosRapidosPanel from "./FiltrosRapidosPanel";
import { useFiltroAvanzadoMutation } from "./api";
import { useFiltrosRapidos } from "./useFiltrosRapidos";
import type {
  ExpedienteBase,
  ExpedienteListSlots,
  ExpedientesAdapter,
  ExpedientesConfig,
  FiltroAvanzadoBase,
  SetToast,
} from "./types";

export type ExpedienteListProps<T extends ExpedienteBase, F extends FiltroAvanzadoBase> =
  ExpedienteListSlots<F> & {
    adapter: ExpedientesAdapter<T, F>;
    config: ExpedientesConfig<T, F>;
    expedientes: T[];
    onSeleccionar: (expediente: T) => void;
    municipioList: Municipio[];
    recursoAfectadoList: ModeloGenerico[];
    setToast: SetToast;
  };

function EstadoVacio({ icono, titulo, texto }: { icono: ReactNode; titulo: string; texto: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="w-16 h-16 bg-base-200 rounded-full flex items-center justify-center mb-4 text-base-content/40">
        {icono}
      </div>
      <h3 className="text-lg font-medium text-base-content/70 mb-2">{titulo}</h3>
      <p className="text-base-content/60 text-sm">{texto}</p>
    </div>
  );
}

/**
 * Lista lateral de expedientes (filtros rápidos locales + búsqueda avanzada
 * en BD + alta opcional). No conoce el módulo: datos por `adapter`,
 * presentación por `config` y alta / filtros extra por slots.
 */
export default function ExpedienteList<T extends ExpedienteBase, F extends FiltroAvanzadoBase>({
  adapter,
  config,
  expedientes,
  onSeleccionar,
  municipioList,
  recursoAfectadoList,
  setToast,
  renderNuevoExpediente,
  renderFiltrosAvanzadosExtra,
}: ExpedienteListProps<T, F>) {
  const [showAdvancedModal, setShowAdvancedModal] = useState(false);
  const [resultadoAvanzado, setResultadoAvanzado] = useState<T[] | null>(null);
  const [isAdding, setIsAdding] = useState(false);

  const filtroAvanzado = useFiltroAvanzadoMutation(adapter);
  const avanzadoActivo = resultadoAvanzado !== null;
  const listaActual = resultadoAvanzado ?? expedientes;

  const filtros = useFiltrosRapidos(listaActual, config.filtrosRapidos);
  const { filtrados } = filtros;

  const aplicarFiltrosAvanzados = (f: F) => {
    filtroAvanzado.mutate(f, {
      onSuccess: (lista) => {
        setResultadoAvanzado(lista);
        setToast({
          id: Date.now(),
          message: `Se encontraron ${lista.length} expedientes`,
          type: "success",
        });
      },
      onError: () =>
        setToast({ id: Date.now(), message: "Error al aplicar filtros avanzados", type: "error" }),
    });
  };

  const limpiarTodo = () => {
    filtros.limpiar();
    setResultadoAvanzado(null);
  };

  const editable = !!renderNuevoExpediente;
  const isLoadingAdvanced = filtroAvanzado.isPending;
  const oculto = isAdding ? "hidden" : "block";

  return (
    <>
      <div className="w-80 flex flex-col h-full bg-base-100">
        {!isAdding && (
          <FiltrosRapidosPanel
            filtros={filtros}
            avanzadoActivo={avanzadoActivo}
            onAbrirAvanzado={() => setShowAdvancedModal(true)}
            onLimpiarTodo={limpiarTodo}
          />
        )}

        {/* RESULTADOS Y ESTADÍSTICAS */}
        <div className={`${oculto} flex-shrink-0 px-6 py-3 bg-base-200 border-b border-base-300`}>
          <div className="flex items-center justify-between text-sm">
            <span className="text-base-content/70">
              {filtrados.length} de {listaActual.length} expedientes
            </span>
            <div className="flex gap-2">
              {avanzadoActivo && (
                <span className="badge badge-success text-white badge-sm">Búsqueda BD</span>
              )}
              {filtrados.length !== listaActual.length && (
                <span className="badge badge-info text-white badge-sm">Filtrado</span>
              )}
              {isLoadingAdvanced && <span className="loading loading-spinner loading-sm"></span>}
            </div>
          </div>
        </div>

        {/* LISTA SCROLLEABLE DE TARJETAS */}
        <div className={`${oculto} flex-1 overflow-y-auto p-4 space-y-3`}>
          {isLoadingAdvanced ? (
            <div className="flex flex-col items-center justify-center py-12">
              <span className="loading loading-spinner loading-lg text-success"></span>
              <p className="text-base-content/60 text-sm mt-4">Buscando en base de datos...</p>
            </div>
          ) : expedientes.length === 0 && !avanzadoActivo ? (
            <EstadoVacio
              icono={<FileText className="w-8 h-8" />}
              titulo="Sin expedientes"
              texto={
                editable
                  ? "¡Comienza creando un nuevo expediente!"
                  : "No hay expedientes disponibles."
              }
            />
          ) : filtrados.length === 0 ? (
            <EstadoVacio
              icono={<Search className="w-8 h-8" />}
              titulo="Sin resultados"
              texto={
                avanzadoActivo
                  ? "No se encontraron expedientes con los criterios avanzados"
                  : "Intenta ajustar los filtros de búsqueda"
              }
            />
          ) : (
            filtrados.map((e) => (
              <ExpedienteCard
                key={e.id}
                titulo={e.radicado}
                onClick={() => onSeleccionar(e)}
                campos={[
                  {
                    etiqueta: config.campoDestacado.etiqueta,
                    valor: config.campoDestacado.valor(e),
                    icono: <FileText />,
                  },
                  {
                    etiqueta: "Municipio",
                    valor: e.municipio?.nombre || "Desconocido",
                    icono: <MapPin />,
                  },
                  {
                    etiqueta: "Fecha de Creación",
                    valor: formatDate(e.fecha_creacion),
                    icono: <CalendarPlus />,
                  },
                ]}
              />
            ))
          )}
        </div>

        {editable && (
          <>
            {/* BOTÓN NUEVO (FIJO) */}
            <div className={`${oculto} flex-shrink-0 p-6 border-t border-base-300 bg-base-100`}>
              <button className="btn btn-success text-white w-full" onClick={() => setIsAdding(true)}>
                + Nuevo Expediente
              </button>
            </div>

            {/* FORMULARIO (montado siempre para conservar lo escrito al ocultarse) */}
            <div className={`${isAdding ? "block" : "hidden"} h-full`}>
              {renderNuevoExpediente({ cerrar: () => setIsAdding(false) })}
            </div>
          </>
        )}
      </div>

      {showAdvancedModal && (
        <FiltroAvanzadoModal
          isOpen={showAdvancedModal}
          onClose={() => setShowAdvancedModal(false)}
          onApplyFilters={aplicarFiltrosAvanzados}
          adapter={adapter}
          config={config}
          municipioList={municipioList}
          recursoAfectadoList={recursoAfectadoList}
          renderExtra={renderFiltrosAvanzadosExtra}
        />
      )}
    </>
  );
}
