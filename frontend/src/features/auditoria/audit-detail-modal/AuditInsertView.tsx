import {
  translateFieldName,
  type AuditData,
  type ValueResolver,
} from "./auditFormatters";

type Props = {
  tablaAfectada: string;
  datosNuevos: AuditData;
  fields: string[];
  resolveValue: ValueResolver;
};

export default function AuditInsertView({
  tablaAfectada,
  datosNuevos,
  fields,
  resolveValue,
}: Props) {
  return (
    <div className="space-y-4">
      <div className="alert alert-success">
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
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <span>
          Nuevo registro creado en la tabla <strong>{tablaAfectada}</strong>
        </span>
      </div>

      <div className="bg-base-200 rounded-lg p-4">
        <h4 className="font-semibold mb-3 text-success flex items-center gap-2">
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
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          Datos Creados
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
                {resolveValue(key, datosNuevos[key])}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
