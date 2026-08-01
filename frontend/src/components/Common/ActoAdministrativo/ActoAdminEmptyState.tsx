type Props = {
  isEditable: boolean;
  onCreate: () => void;
  /** Modal de creación (se renderiza sólo cuando es editable). */
  children?: React.ReactNode;
};

const DocumentIcon = ({ className }: { className: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
    />
  </svg>
);

/** Vista cuando la etapa no tiene acto administrativo registrado. */
export default function ActoAdminEmptyState({
  isEditable,
  onCreate,
  children,
}: Props) {
  if (!isEditable) {
    return (
      <div className="card bg-base-100 shadow-md border border-base-300">
        <div className="card-body">
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-base-200 rounded-full flex items-center justify-center mb-4 mx-auto">
              <DocumentIcon className="w-8 h-8 text-base-content/40" />
            </div>
            <h3 className="text-lg font-medium text-base-content/70 mb-2">
              Sin acto administrativo
            </h3>
            <p className="text-base-content/60">
              No hay acto administrativo registrado para esta etapa
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card bg-base-100 shadow-md border border-base-300">
      <div className="card-body">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
              <DocumentIcon className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h3 className="text-xl font-bold">Acto Administrativo</h3>
              <p className="text-sm text-base-content/60">
                Registra el acto administrativo de la etapa
              </p>
            </div>
          </div>
          <button
            onClick={onCreate}
            className="btn btn-ghost btn-sm gap-2 text-primary hover:bg-primary/10"
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
                d="M12 4v16m8-8H4"
              />
            </svg>
            Crear
          </button>
        </div>

        <div className="bg-base-200/50 rounded-lg p-6 text-center">
          <DocumentIcon className="w-12 h-12 text-base-content/30 mx-auto mb-3" />
          <p className="text-base-content/60 text-sm">
            No hay acto administrativo registrado
          </p>
        </div>
      </div>

      {children}
    </div>
  );
}
