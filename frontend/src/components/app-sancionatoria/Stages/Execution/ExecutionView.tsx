type Execution = {
  id?: number;
  cobro_coactivo: boolean;
  cobro_coactivo_doc_url: string | null;
  disposicion: boolean;
  ruia: boolean;
  ruia_doc_url: string | null;
  memorando: boolean;
  memorando_doc_url: string | null;
  auto_admin: string;
  fecha_auto: string | null;
  auto_doc_url: string | null;
  etapa_id: number;
};

type Props = {
  data: Execution;
  onViewDocument: (url: string) => void;
};

const formatDate = (fecha: string | null) => {
  if (!fecha) return "No registrada";
  const [year, month, day] = fecha.split("-");
  const meses = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
  ];
  return `${parseInt(day)} de ${meses[parseInt(month) - 1]} de ${year}`;
};

const formatAutoAdmin = (autoAdmin: string) => {
  if (!autoAdmin) return "No registrado";
  const match = autoAdmin.match(/^(AUTO|RES)(.*)$/);
  if (match) {
    return `${match[1]} ${match[2]}`;
  }
  return autoAdmin;
};

export default function ExecutionView({ data, onViewDocument }: Props) {
  return (
    <div className="space-y-6">
      {/* Estados de documentos en una línea horizontal */}
      <div className="flex flex-wrap items-center gap-6">
        {/* Cobro Coactivo */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-base-content/70">
            Cobro Coactivo
          </span>
          <span
            className={`badge text-white badge-sm ${
              data.cobro_coactivo ? "badge-success" : "badge-error"
            }`}
          >
            {data.cobro_coactivo ? "Sí" : "No"}
          </span>
          {/* ✨ Solo mostrar botón si está marcado como SÍ Y tiene documento */}
          {data.cobro_coactivo && data.cobro_coactivo_doc_url && (
            <button
              onClick={() => onViewDocument(data.cobro_coactivo_doc_url!)}
              className="btn btn-ghost btn-xs text-info hover:bg-info/10"
              title="Ver documento"
            >
              <svg
                className="w-5 h-5 text-error"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" />
              </svg>
            </button>
          )}
        </div>

        <div className="divider divider-horizontal mx-0"></div>

        {/* RUIA */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-base-content/70">RUIA</span>
          <span
            className={`badge text-white badge-sm ${
              data.ruia ? "badge-success" : "badge-error"
            }`}
          >
            {data.ruia ? "Sí" : "No"}
          </span>
          {/* ✨ Solo mostrar botón si está marcado como SÍ Y tiene documento */}
          {data.ruia && data.ruia_doc_url && (
            <button
              onClick={() => onViewDocument(data.ruia_doc_url!)}
              className="btn btn-ghost btn-xs text-info hover:bg-info/10"
              title="Ver documento"
            >
              <svg
                className="w-5 h-5 text-info"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" />
              </svg>
            </button>
          )}
        </div>

        <div className="divider divider-horizontal mx-0"></div>

        {/* Memorando */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-base-content/70">
            Memorando
          </span>
          <span
            className={`badge text-white badge-sm ${
              data.memorando ? "badge-success" : "badge-error"
            }`}
          >
            {data.memorando ? "Sí" : "No"}
          </span>
          {/* ✨ Solo mostrar botón si está marcado como SÍ Y tiene documento */}
          {data.memorando && data.memorando_doc_url && (
            <button
              onClick={() => onViewDocument(data.memorando_doc_url!)}
              className="btn btn-ghost btn-xs text-info hover:bg-info/10"
              title="Ver documento"
            >
              <svg
                className="w-5 h-5 text-info"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" />
              </svg>
            </button>
          )}
        </div>

        <div className="divider divider-horizontal mx-0"></div>

        {/* Disposición */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-base-content/70">
            Disposición
          </span>
          <span
            className={`badge text-white badge-sm ${
              data.disposicion ? "badge-success" : "badge-error"
            }`}
          >
            {data.disposicion ? "Sí" : "No"}
          </span>
        </div>
      </div>

      <div className="divider my-4"></div>

      {/* Acto Administrativo en sección separada */}
      <div className="bg-base-200/50 rounded-lg p-6">
        <h4 className="font-semibold text-base mb-4 flex items-center gap-2">
          <svg
            className="w-5 h-5 text-primary"
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
          Acto Administrativo
        </h4>

        <div className="flex items-center gap-4">
          <div className="flex-1">
            <p className="text-sm text-base-content/60 mb-1">Número del acto</p>
            <p className="text-lg font-bold font-mono">
              {formatAutoAdmin(data.auto_admin)}
            </p>
          </div>
          <div className="flex-1">
            <p className="text-sm text-base-content/60 mb-1">Fecha</p>
            <p className="text-base font-semibold">
              {formatDate(data.fecha_auto)}
            </p>
          </div>
          {data.auto_doc_url && (
            <div className="flex-shrink-0">
              <button
                onClick={() => onViewDocument(data.auto_doc_url!)}
                className="btn btn-ghost btn-xs text-info hover:bg-info/10"
                title="Ver documento"
              >
                <svg
                  className="w-8 h-8 text-error"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M15.5,15.5L13,19L11.5,15.5L8,14L11.5,12.5L13,9L14.5,12.5L18,14L15.5,15.5M13,3.5L17.5,8H13V3.5Z" />
                </svg>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
