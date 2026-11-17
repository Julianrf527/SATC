import { useState } from "react";
import { openDocumentById, isValidDocumentId } from "@shared/lib/documentViewer";
import type { Ejecucion, SetToast } from "../../types";
import SeccionDatos from "../comun/SeccionDatos";
import SinInformacion from "../comun/SinInformacion";
import { ICONOS } from "../comun/iconos";
import ExecutionView from "./EjecucionView";
import ExecutionForm from "./EjecucionForm";
import { useEjecucionForm } from "./useEjecucionForm";

type Props = {
  data: Ejecucion | undefined;
  setToast: SetToast;
  expedienteId: number;
  onDataUpdated?: () => void;
  isEditable?: boolean;
};

export default function EjecucionSancionData({
  data,
  setToast,
  expedienteId,
  onDataUpdated,
  isEditable = true,
}: Props) {
  const [showForm, setShowForm] = useState(!data && isEditable);
  const form = useEjecucionForm({
    data,
      expedienteId,
    setToast,
    onGuardado: () => {
      setShowForm(false);
      onDataUpdated?.();
    },
  });

  const handleViewDocument = (documentId: number) => {
    if (isValidDocumentId(documentId)) openDocumentById(documentId);
  };

  return (
    <SeccionDatos
      titulo="Ejecución de la Sanción"
      icono={ICONOS.portapapeles}
      tono="primary"
      subtitulo={
        data
          ? "Información sobre la ejecución"
          : isEditable
            ? "Registra información de ejecución"
            : "No hay ejecución registrada"
      }
      onEditar={!showForm && data && isEditable ? () => setShowForm(true) : undefined}
      textoEditar=""
      deshabilitado={form.isLoading}
    >
      {!showForm && data && <ExecutionView data={data} onViewDocument={handleViewDocument} />}

      {!showForm && !data && !isEditable && (
        <SinInformacion
          punteado
          icono={ICONOS.documento}
          titulo="Sin ejecución registrada"
          texto="No hay información de ejecución para este expediente"
        />
      )}

      {showForm && isEditable && (
        <ExecutionForm
          data={data}
          form={form}
          onCancel={() => data && setShowForm(false)}
          onViewDocument={handleViewDocument}
        />
      )}
    </SeccionDatos>
  );
}
