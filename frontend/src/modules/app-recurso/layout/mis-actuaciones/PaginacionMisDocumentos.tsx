import { paginasVisibles } from "../../api/misDocumentosParams";

type Props = {
  page: number;
  totalPages: number;
  onPage: (page: number) => void;
  deshabilitado: boolean;
};

/** Controles de página (mismo aspecto que el listado de informes de infraction). */
export default function PaginacionMisDocumentos({ page, totalPages, onPage, deshabilitado }: Props) {
  if (totalPages <= 1) return null;
  return (
    <div className="flex justify-center items-center gap-2 p-4 border-t border-base-200">
      <button type="button" className="btn btn-sm btn-ghost" disabled={page <= 1 || deshabilitado} onClick={() => onPage(page - 1)}>
        «
      </button>
      {paginasVisibles(page, totalPages).map((p) => (
        <button
          key={p}
          type="button"
          className={`btn btn-sm ${p === page ? "btn-success text-white" : "btn-ghost"}`}
          onClick={() => onPage(p)}
          disabled={deshabilitado}
        >
          {p}
        </button>
      ))}
      <button
        type="button"
        className="btn btn-sm btn-ghost"
        disabled={page >= totalPages || deshabilitado}
        onClick={() => onPage(page + 1)}
      >
        »
      </button>
    </div>
  );
}
