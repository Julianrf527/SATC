type CardProps = {
  expediente_id: number;
  radicado: string;
  expediente: string;
  municipio: string;
  fecha_creacion: string;
  onClick: () => void;
};

export default function FileCard({
  radicado,
  expediente,
  municipio,
  fecha_creacion,
  onClick,
}: CardProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("es-ES", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  };

  return (
    <div
      className="card bg-base-100 border border-base-300 cursor-pointer 
                 hover:border-success hover:shadow-lg transition-all duration-200
                 hover:-translate-y-0.5 active:translate-y-0"
      onClick={onClick}
    >
      <div className="card-body p-4">
        {/* Header con radicado */}
        <div className="flex items-center justify-between mb-3">
          <h3 className="card-title text-base font-bold truncate">{radicado}</h3>
        </div>

        {/* Información del expediente */}
        <div className="space-y-2">
          <div className="flex items-start gap-2">
            <svg
              className="w-4 h-4 text-base-content/40 mt-0.5 flex-shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <div>
              <p className="text-xs text-base-content/50 uppercase tracking-wide font-medium">
                Expediente
              </p>
              <p className="text-sm text-base-content leading-tight">
                {expediente}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-2">
            <svg
              className="w-4 h-4 text-base-content/40 mt-0.5 flex-shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
            <div>
              <p className="text-xs text-base-content/50 uppercase tracking-wide font-medium">
                Municipio
              </p>
              <p className="text-sm text-base-content leading-tight">
                {municipio}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-2">
            <svg
              className="w-4 h-4 text-base-content/40 mt-0.5 flex-shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 7V3a1 1 0 011-1h6a1 1 0 011 1v4m-6 0h6m-6 0a1 1 0 00-1 1v10a1 1 0 001 1h6a1 1 0 001-1V8a1 1 0 00-1-1"
              />
            </svg>
            <div>
              <p className="text-xs text-base-content/50 uppercase tracking-wide font-medium">
                Fecha de Creación
              </p>
              <p className="text-sm text-base-content leading-tight">
                {formatDate(fecha_creacion)}
              </p>
            </div>
          </div>
        </div>

        {/* Indicador visual de hover */}
        <div className="mt-3 pt-3 border-t border-base-300">
          <div className="flex items-center justify-between">
            <span className="text-xs text-base-content/40">
              Click para ver detalles
            </span>
            <svg
              className="w-4 h-4 text-base-content/40"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5l7 7-7-7"
              />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}
