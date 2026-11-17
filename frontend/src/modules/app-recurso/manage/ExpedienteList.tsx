import { useState, type ReactNode } from "react";
import { ChevronLeft, ChevronRight, FileText, Search } from "lucide-react";
import { useErrorToast } from "@shared/hooks/useErrorToast";
import { useExpedientesQuery } from "../api/expedientes";
import { FILTROS_LISTA_INICIALES, totalPaginas, type FiltrosListaExpedientes } from "../api/listaParams";
import type { CatalogosRecurso, SetToast } from "../types";
import ExpedienteCard from "./lista/ExpedienteCard";
import FiltrosListaPanel from "./lista/FiltrosListaPanel";
import { useValorDiferido } from "./lista/useValorDiferido";
import NuevoExpediente from "./NuevoExpediente";

type Props = {
  catalogos: CatalogosRecurso;
  setToast: SetToast;
  seleccionadoId: number | null;
  onSeleccionar: (expedienteId: number) => void;
  /** Muestra "+ Nuevo Expediente" (Gestionar). En Consulta se omite. */
  puedeCrear: boolean;
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
 * Lista lateral de expedientes de concesiones. Réplica visual de
 * `@features/expedientes/ExpedienteList`: aquella filtra en cliente sobre la
 * lista completa y su modal avanzado trae "Recursos afectados" fijo; este
 * listado es paginado y se filtra en el backend (API.md A.2), así que no
 * encaja sin modificar la feature.
 */
export default function ExpedienteList({ catalogos, setToast, seleccionadoId, onSeleccionar, puedeCrear }: Props) {
  const [filtros, setFiltros] = useState<FiltrosListaExpedientes>(FILTROS_LISTA_INICIALES);
  const [creando, setCreando] = useState(false);
  const filtrosConsulta = useValorDiferido(filtros);

  const lista = useExpedientesQuery(filtrosConsulta);
  useErrorToast(lista.error, setToast, "Error al cargar los expedientes");

  const expedientes = lista.data?.data ?? [];
  const total = lista.data?.totalCount ?? 0;
  const paginas = totalPaginas(total, filtros.limit);
  const hayFiltros = JSON.stringify({ ...filtros, page: 1 }) !== JSON.stringify(FILTROS_LISTA_INICIALES);

  const cambiarFiltros = (cambio: Partial<FiltrosListaExpedientes>) =>
    setFiltros((prev) => ({ ...prev, ...cambio, page: cambio.page ?? 1 }));

  const oculto = creando ? "hidden" : "block";

  return (
    <div className="w-80 flex flex-col h-full bg-base-100">
      {!creando && (
        <FiltrosListaPanel filtros={filtros} onChange={cambiarFiltros} municipios={catalogos.municipios} setToast={setToast} />
      )}

      <div className={`${oculto} flex-shrink-0 px-6 py-3 bg-base-200 border-b border-base-300`}>
        <div className="flex items-center justify-between text-sm">
          <span className="text-base-content/70">
            {expedientes.length} de {total} expedientes
          </span>
          <div className="flex gap-2 items-center">
            {hayFiltros && <span className="badge badge-info text-white badge-sm">Filtrado</span>}
            {lista.isFetching && <span className="loading loading-spinner loading-sm" />}
          </div>
        </div>
      </div>

      <div className={`${oculto} flex-1 overflow-y-auto p-4 space-y-3`}>
        {lista.isPending ? (
          <div className="flex flex-col items-center justify-center py-12">
            <span className="loading loading-spinner loading-lg text-success" />
            <p className="text-base-content/60 text-sm mt-4">Buscando en base de datos...</p>
          </div>
        ) : expedientes.length === 0 ? (
          hayFiltros ? (
            <EstadoVacio icono={<Search className="w-8 h-8" />} titulo="Sin resultados" texto="Intenta ajustar los filtros de búsqueda" />
          ) : (
            <EstadoVacio
              icono={<FileText className="w-8 h-8" />}
              titulo="Sin expedientes"
              texto={puedeCrear ? "¡Comienza creando un nuevo expediente!" : "No hay expedientes disponibles."}
            />
          )
        ) : (
          expedientes.map((e) => (
            <ExpedienteCard key={e.id} expediente={e} seleccionado={e.id === seleccionadoId} onClick={() => onSeleccionar(e.id)} />
          ))
        )}
      </div>

      {paginas > 1 && (
        <div className={`${oculto} flex-shrink-0 flex items-center justify-between px-4 py-2 border-t border-base-300 text-sm`}>
          <button
            type="button"
            className="btn btn-ghost btn-xs"
            disabled={filtros.page <= 1}
            onClick={() => cambiarFiltros({ page: filtros.page - 1 })}
            aria-label="Página anterior"
          >
            <ChevronLeft size={14} />
          </button>
          <span className="text-base-content/70">
            Página {filtros.page} de {paginas}
          </span>
          <button
            type="button"
            className="btn btn-ghost btn-xs"
            disabled={filtros.page >= paginas}
            onClick={() => cambiarFiltros({ page: filtros.page + 1 })}
            aria-label="Página siguiente"
          >
            <ChevronRight size={14} />
          </button>
        </div>
      )}

      {puedeCrear && (
        <>
          <div className={`${oculto} flex-shrink-0 p-6 border-t border-base-300 bg-base-100`}>
            <button type="button" className="btn btn-success text-white w-full" onClick={() => setCreando(true)}>
              + Nuevo Expediente
            </button>
          </div>

          {/* Montado siempre para conservar lo escrito al ocultarse */}
          <div className={`${creando ? "block" : "hidden"} h-full`}>
            <NuevoExpediente
              catalogos={catalogos}
              setToast={setToast}
              onCancel={() => setCreando(false)}
              onCreado={onSeleccionar}
            />
          </div>
        </>
      )}
    </div>
  );
}
