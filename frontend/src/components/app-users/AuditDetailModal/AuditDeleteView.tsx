import {
  translateFieldName,
  type AuditData,
  type ValueResolver,
} from "./auditFormatters";

type Props = {
  tablaAfectada: string;
  datosAnteriores: AuditData;
  fields: string[];
  resolveValue: ValueResolver;
};

export default function AuditDeleteView({
  tablaAfectada,
  datosAnteriores,
  fields,
  resolveValue,
}: Props) {
  return (
    <div className="space-y-4">
      <div className="alert alert-error">
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        <span>
          Registro eliminado de la tabla <strong>{tablaAfectada}</strong>
        </span>
      </div>

      <div className="bg-base-200 rounded-lg p-4">
        <h4 className="font-semibold mb-3 text-error flex items-center gap-2">
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
            />
          </svg>
          Datos Eliminados
        </h4>
        <div className="grid grid-cols-1 gap-3">
          {fields.map((key) => (
            <div
              key={key}
              className="flex justify-between items-start border-b border-base-300 pb-2"
            >
              <span className="font-medium text-base-content/80">
                {translateFieldName(key)}:
              </span>
              <span className="text-right max-w-md break-words">
                {resolveValue(key, datosAnteriores[key])}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
