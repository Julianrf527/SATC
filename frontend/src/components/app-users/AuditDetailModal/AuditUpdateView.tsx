import {
  getChangedFields,
  translateFieldName,
  type AuditData,
  type ValueResolver,
} from "./auditFormatters";

type Props = {
  tablaAfectada: string;
  datosAnteriores: AuditData;
  datosNuevos: AuditData;
  resolveValue: ValueResolver;
};

export default function AuditUpdateView({
  tablaAfectada,
  datosAnteriores,
  datosNuevos,
  resolveValue,
}: Props) {
  const changedFields = getChangedFields(datosAnteriores, datosNuevos);

  // Si es inicio/cierre de sesión, vista simplificada
  if (datosNuevos?.fecha_login) {
    return (
      <div className="space-y-4">
        <div className="alert alert-info">
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
          <span>Evento de sesión de usuario</span>
        </div>

        <div className="bg-base-200 rounded-lg p-4">
          <div className="space-y-3">
            {["usuario_id", "nombre_completo", "fecha_login"].map(
              (key) =>
                datosNuevos[key] && (
                  <div key={key} className="flex justify-between items-start">
                    <span className="font-medium text-base-content/80">
                      {translateFieldName(key)}:
                    </span>
                    <span className="text-right">
                      {resolveValue(key, datosNuevos[key])}
                    </span>
                  </div>
                ),
            )}
          </div>
        </div>
      </div>
    );
  }

  if (changedFields.length === 0) {
    return (
      <div className="alert alert-warning">
        <span>No se detectaron cambios en los datos</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="alert alert-warning">
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
          Se modificaron <strong>{changedFields.length}</strong> campo(s) en{" "}
          <strong>{tablaAfectada}</strong>
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Datos Anteriores */}
        <div className="bg-error/10 rounded-lg p-4">
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
                d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            Valores Anteriores
          </h4>
          <div className="space-y-3">
            {changedFields.map((key) => (
              <div key={key} className="bg-base-100 rounded p-2">
                <div className="font-medium text-sm text-base-content/70 mb-1">
                  {translateFieldName(key)}
                </div>
                <div className="text-error font-medium break-words">
                  {resolveValue(key, datosAnteriores[key])}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Datos Nuevos */}
        <div className="bg-success/10 rounded-lg p-4 border-2 border-success/20">
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
            Valores Nuevos
          </h4>
          <div className="space-y-3">
            {changedFields.map((key) => (
              <div key={key} className="bg-base-100 rounded p-2">
                <div className="font-medium text-sm text-base-content/70 mb-1">
                  {translateFieldName(key)}
                </div>
                <div className="text-success font-medium break-words">
                  {resolveValue(key, datosNuevos[key])}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
