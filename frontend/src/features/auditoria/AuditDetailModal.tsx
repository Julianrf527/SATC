import AuditDeleteView from "./audit-detail-modal/AuditDeleteView";
import AuditInsertView from "./audit-detail-modal/AuditInsertView";
import AuditOperationIcon from "./audit-detail-modal/AuditOperationIcon";
import AuditUpdateView from "./audit-detail-modal/AuditUpdateView";
import {
  createValueResolver,
  getRelevantFields,
  type AuditData,
} from "./audit-detail-modal/auditFormatters";
import { useAuditMappings } from "./audit-detail-modal/useAuditMappings";
import { Modal } from "@shared/ui";
import type { AuditMappingSources } from "./types";

type AuditDetailModalProps = {
  isOpen: boolean;
  onClose: () => void;
  titulo: string;
  tipoOperacion: string;
  tablaAfectada: string;
  datosAnteriores: AuditData;
  datosNuevos: AuditData;
  /**
   * Catálogos para traducir IDs (municipios, recursos...) que inyecta el
   * módulo. Roles, permisos y etapas se resuelven siempre.
   */
  mappingSources: AuditMappingSources;
};

const operationColors = {
  INSERT: "text-success",
  UPDATE: "text-tono-warning",
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
  mappingSources,
}: AuditDetailModalProps) {
  const { mappingCache, loading } = useAuditMappings(
    isOpen,
    mappingSources,
    datosAnteriores,
    datosNuevos,
  );

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
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      size="4xl"
      className="!max-w-5xl"
      icon={
        <span
          className={
            operationColors[tipoOperacion as keyof typeof operationColors]
          }
        >
          <AuditOperationIcon tipoOperacion={tipoOperacion} />
        </span>
      }
      title={
        <>
          {operationNames[tipoOperacion as keyof typeof operationNames]} -{" "}
          {tablaAfectada
            ? tablaAfectada.charAt(0).toUpperCase() + tablaAfectada.slice(1)
            : "—"}
        </>
      }
      subtitle="Detalles completos de la operación realizada"
      footer={
        <button className="btn btn-ghost" onClick={onClose}>
          Cerrar
        </button>
      }
    >
      {loading ? (
        <div className="flex justify-center items-center py-12">
          <span className="loading loading-spinner loading-lg text-success"></span>
        </div>
      ) : (
        renderContent()
      )}
    </Modal>
  );
}
