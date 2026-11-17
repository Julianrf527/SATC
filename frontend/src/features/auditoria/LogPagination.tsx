import type { ReactNode } from "react";

type Props = {
  /** Texto "Mostrando X de Y registros". */
  resumen: ReactNode;
  displayedPage: number;
  totalPages: number;
  isEmpty: boolean;
  onPrevious: () => void;
  onNext: () => void;
};

/** Pie de la tabla de logs: resumen + anterior / página / siguiente. */
export default function LogPagination({
  resumen,
  displayedPage,
  totalPages,
  isEmpty,
  onPrevious,
  onNext,
}: Props) {
  return (
    <div className="flex justify-between items-center pt-4 border-t border-base-300 mt-4">
      <div className="text-sm text-base-content/60">
        {resumen}
      </div>
      <div className="join">
        <button
          className="join-item btn btn-sm"
          disabled={displayedPage === 1 || isEmpty}
          onClick={onPrevious}
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
        </button>
        <button className="join-item btn btn-sm no-animation">
          Página {isEmpty ? 0 : displayedPage} de {totalPages}
        </button>
        <button
          className="join-item btn btn-sm"
          disabled={displayedPage >= totalPages || isEmpty}
          onClick={onNext}
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
        </button>
      </div>
    </div>
  );
}
