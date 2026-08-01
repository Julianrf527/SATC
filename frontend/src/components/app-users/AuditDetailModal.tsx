import AuditDeleteView from "./AuditDetailModal/AuditDeleteView";
import AuditInsertView from "./AuditDetailModal/AuditInsertView";
import AuditOperationIcon from "./AuditDetailModal/AuditOperationIcon";
import AuditUpdateView from "./AuditDetailModal/AuditUpdateView";
import {
  createValueResolver,
  getRelevantFields,
  type AuditData,
} from "./AuditDetailModal/auditFormatters";
import {
  useAuditMappings,
  type AuditScope,
} from "./AuditDetailModal/useAuditMappings";

type AuditDetailModalProps = {
  isOpen: boolean;
  onClose: () => void;
  titulo: string;
  tipoOperacion: string;
  tablaAfectada: string;
  datosAnteriores: AuditData;
  datosNuevos: AuditData;
  auditScope: AuditScope;
};

const operationColors = {
  INSERT: "text-success",
  UPDATE: "text-warning",
  DELETE: "text-error",
};

const operationNames = {
  INSERT: "Creación",
  UPDATE: "Actualización",
  DELETE: "Eliminación",
};

export default function AuditDetailModal({
  isOpen,
  onClose,
  tipoOperacion,
  tablaAfectada,
  datosAnteriores,
  datosNuevos,
  auditScope,
}: AuditDetailModalProps) {
  const { mappingCache, loading } = useAuditMappings(
    isOpen,
    auditScope,
    datosAnteriores,
    datosNuevos,
  );

  if (!isOpen) return null;

  const resolveValue = createValueResolver(mappingCache);

  const renderContent = () => {
    if (tipoOperacion === "INSERT") {
      return (
        <AuditInsertView
          tablaAfectada={tablaAfectada}
          datosNuevos={datosNuevos}
          fields={getRelevantFields(datosNuevos, tablaAfectada, tipoOperacion)}
          resolveValue={resolveValue}
        />
      );
    }

    if (tipoOperacion === "UPDATE") {
      return (
        <AuditUpdateView
          tablaAfectada={tablaAfectada}
          datosAnteriores={datosAnteriores}
          datosNuevos={datosNuevos}
          resolveValue={resolveValue}
        />
      );
    }

    if (tipoOperacion === "DELETE") {
      return (
        <AuditDeleteView
          tablaAfectada={tablaAfectada}
          datosAnteriores={datosAnteriores}
          fields={getRelevantFields(
            datosAnteriores,
            tablaAfectada,
            tipoOperacion,
          )}
          resolveValue={resolveValue}
        />
      );
    }

    return (
      <div className="alert alert-info">
        <span>Tipo de operación desconocido</span>
      </div>
    );
  };

  return (
    <div className="modal modal-open">
      <div className="modal-box max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center gap-3 mb-4 pb-4 border-b border-base-300">
          <div
            className={`w-12 h-12 rounded-full flex items-center justify-center ${
              tipoOperacion === "INSERT"
                ? "bg-success/20"
                : tipoOperacion === "UPDATE"
                  ? "bg-warning/20"
                  : "bg-error/20"
            } ${operationColors[tipoOperacion as keyof typeof operationColors]}`}
          >
            <AuditOperationIcon tipoOperacion={tipoOperacion} />
          </div>
          <div className="flex-1">
            <h3 className="font-bold text-xl">
              {operationNames[tipoOperacion as keyof typeof operationNames]} -{" "}
              {tablaAfectada
                ? tablaAfectada.charAt(0).toUpperCase() + tablaAfectada.slice(1)
                : "—"}
            </h3>
            <p className="text-sm text-base-content/60">
              Detalles completos de la operación realizada
            </p>
          </div>
          <button onClick={onClose} className="btn btn-ghost btn-sm btn-circle">
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex justify-center items-center py-12">
              <span className="loading loading-spinner loading-lg text-success"></span>
            </div>
          ) : (
            renderContent()
          )}
        </div>

        {/* Footer */}
        <div className="modal-action mt-4 pt-4 border-t border-base-300">
          <button className="btn btn-ghost" onClick={onClose}>
            Cerrar
          </button>
        </div>
      </div>
      <div className="modal-backdrop bg-black/50" onClick={onClose}></div>
    </div>
  );
}
