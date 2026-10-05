import { ChevronLeft, ChevronRight } from "lucide-react";

type Props = {
  page: number;
  totalPages: number;
  onPage: (page: number) => void;
};

/** Botones 1 … p-2..p+2 … N. */
function paginas(page: number, total: number): (number | "...")[] {
  const out: (number | "...")[] = [];
  let prev = 0;
  for (let i = 1; i <= total; i++) {
    if (i === 1 || i === total || (i >= page - 2 && i <= page + 2)) {
      if (prev && i - prev > 1) out.push("...");
      out.push(i);
      prev = i;
    }
  }
  return out;
}

export default function Paginacion({ page, totalPages, onPage }: Props) {
  if (totalPages <= 1) return null;
  return (
    <nav aria-label="Paginación" className="flex flex-col items-center gap-2 mt-8">
      <div className="join">
        <button className="join-item btn btn-sm" onClick={() => onPage(page - 1)} disabled={page === 1} aria-label="Anterior">
          <ChevronLeft size={16} />
        </button>
        {paginas(page, totalPages).map((p, idx) =>
          p === "..." ? (
            <span key={`e-${idx}`} className="join-item btn btn-sm btn-disabled">…</span>
          ) : (
            <button
              key={p}
              className={`join-item btn btn-sm ${p === page ? "btn-success text-white" : ""}`}
              onClick={() => onPage(p)}
              aria-current={p === page ? "page" : undefined}
            >
              {p}
            </button>
          ),
        )}
        <button
          className="join-item btn btn-sm"
          onClick={() => onPage(page + 1)}
          disabled={page === totalPages}
          aria-label="Siguiente"
        >
          <ChevronRight size={16} />
        </button>
      </div>
      <p className="text-xs text-base-content/60">
        Página {page} de {totalPages}
      </p>
    </nav>
  );
}
