import { useEffect, useState, useRef } from "react";
import type { RespuestaData } from "../../types";
import { useGuardarRespuestaMutation } from "../../api/etapas";
import { detalleError, esErrorDeConexion, estadoError } from "../../api/errors";
import RespuestaDataView from "./RespuestaDataView";
import RespuestaForm from "./RespuestaForm";
import {
  uploadFileToDocuments,
  generateDocumentFileName,
} from "@shared/lib/fileUpload";

type Props = {
  expedienteId: number;
  handleViewDocument: (fileId: number) => void;
  respuestaData: RespuestaData | null;
  isCreatingStage: boolean;
  setIsCreatingStage: (value: boolean) => void;
  isEditable: boolean;
  setToast: (toast: {
    id: number;
    type: "success" | "error";
    message: string;
  }) => void;
  onSaveSuccess?: () => void;
};

export default function RespuestaData({
  expedienteId,
  respuestaData,
  isCreatingStage,
  setIsCreatingStage,
  isEditable,
  setToast,
  handleViewDocument,
  onSaveSuccess,
}: Props) {
  const [showForm, setShowForm] = useState(isCreatingStage);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUploadingFile, setIsUploadingFile] = useState(false);

  const [selectedRadicado, setSelectedRadicado] = useState(
    respuestaData?.radicado || "",
  );
  const [selectedFechaRadicado, setSelectedFechaRadicado] = useState(
    respuestaData?.fecha_radicado || "",
  );
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [medidaChecked, setMedidaChecked] = useState(
    respuestaData?.requiere_medida_preventiva || false,
  );
  const fileInputRef = useRef<HTMLInputElement>(null);
  const guardarRespuesta = useGuardarRespuestaMutation(expedienteId);

  const handleCancel = () => {
    setShowForm(false);
    setIsCreatingStage(false);
    if (respuestaData) {
      setSelectedRadicado(respuestaData.radicado || "");
      setSelectedFechaRadicado(respuestaData.fecha_radicado || "");
      setMedidaChecked(respuestaData.requiere_medida_preventiva || false);
    }
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleViewFile = () => {
    if (respuestaData?.documento_radicado_id) {
      handleViewDocument(respuestaData.documento_radicado_id);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  useEffect(() => {
    if (isCreatingStage) {
      setShowForm(true);
    }
  }, [isCreatingStage]);

  useEffect(() => {
    if (respuestaData) {
      setSelectedRadicado(respuestaData.radicado || "");
      setSelectedFechaRadicado(respuestaData.fecha_radicado || "");
      setMedidaChecked(respuestaData.requiere_medida_preventiva || false);
    } else if (!isCreatingStage) {
      setSelectedRadicado("");
      setSelectedFechaRadicado("");
      setMedidaChecked(false);
    }
  }, [respuestaData, isCreatingStage]);

  const handleSave = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!selectedFechaRadicado) {
      setToast({ id: Date.now(), message: "Seleccione la fecha de radicado", type: "error" });
      return;
    }

    setIsSubmitting(true);

    try {
      let documento_id: number | undefined;

      // Paso 1: Si hay archivo seleccionado, subirlo a app-docs primero
      if (selectedFile) {
        setIsUploadingFile(true);
        try {
          const fileName = generateDocumentFileName("Auto", selectedRadicado, selectedFechaRadicado);
          documento_id = await uploadFileToDocuments(selectedFile, fileName);
        } finally {
          setIsUploadingFile(false);
        }
      }

      if (!documento_id && respuestaData?.documento_radicado_id) {
        documento_id = respuestaData.documento_radicado_id;
      }

      if (!documento_id) {
        setToast({
          id: Date.now(),
          type: "error",
          message: "Debe adjuntar un documento para guardar la respuesta",
        });
        return;
      }

      // Paso 2: Enviar datos al endpoint de infracciones
      const respuestaDataCall = {
        radicado: selectedRadicado,
        fecha_radicado: selectedFechaRadicado,
        documento_radicado_id: documento_id,
        requiere_medida_preventiva: medidaChecked,
      };

      if (!isCreatingStage && !respuestaData?.id) {
        setToast({
          id: Date.now(),
          type: "error",
          message: "No se encontró la respuesta para actualizar",
        });
        return;
      }

      try {
        await guardarRespuesta.mutateAsync({
          respuestaId: isCreatingStage ? null : (respuestaData?.id ?? null),
          payload: respuestaDataCall,
        });
      } catch (err) {
        if (esErrorDeConexion(err)) throw err;
        const mensaje =
          estadoError(err) === 409
            ? (detalleError(err) ?? "El radicado ya existe en otra respuesta")
            : "Error al guardar la respuesta";
        setToast({ id: Date.now(), type: "error", message: mensaje });
        return;
      }

      setToast({
        id: Date.now(),
        type: "success",
        message: isCreatingStage
          ? "Etapa respuesta creada correctamente"
          : "Etapa respuesta actualizada correctamente",
      });
      handleClose();
      // La mutación ya re-consultó la etapa: el padre solo actualiza la etapa actual.
      onSaveSuccess?.();
    } catch {
      setToast({
        id: Date.now(),
        type: "error",
        message: "Error al guardar la etapa",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setShowForm(false);
    setIsCreatingStage(false);
    if (!respuestaData) {
      setSelectedRadicado("");
      setSelectedFechaRadicado("");
      setMedidaChecked(false);
    }
    setSelectedFile(null);
    setIsSubmitting(false);
    setIsUploadingFile(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="card bg-base-100 shadow-md border border-base-300">
      <div className="card-body">
        {/* HEADER */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-info/10 rounded-lg flex items-center justify-center">
              <svg
                className="w-5 h-5 text-info"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m-6 8h6a2 2 0 002-2V7l-3-3H7a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-xl font-bold">Datos de la Respuesta</h3>
              <p className="text-sm text-base-content/60">
                {respuestaData
                  ? "Información de la respuesta registrada"
                  : isEditable
                    ? "Registra una nueva respuesta"
                    : "No hay respuesta registrada"}
              </p>
            </div>
          </div>
          {!showForm && isEditable && respuestaData && (
            <button
              className="btn btn-ghost btn-sm gap-2 text-tono-info hover:bg-info/10"
              onClick={() => setShowForm(true)}
              disabled={isSubmitting}
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
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                />
              </svg>
              Editar
            </button>
          )}
        </div>
        {/* FORMULARIO DE CREACIÓN/EDICIÓN */}
        {showForm && isEditable && (
          <RespuestaForm
            respuestaData={respuestaData}
            radicado={selectedRadicado}
            onRadicadoChange={setSelectedRadicado}
            fechaRadicado={selectedFechaRadicado}
            onFechaRadicadoChange={setSelectedFechaRadicado}
            requiereMedida={medidaChecked}
            onRequiereMedidaChange={setMedidaChecked}
            selectedFile={selectedFile}
            onFileChange={handleFileChange}
            fileInputRef={fileInputRef}
            isSubmitting={isSubmitting}
            isUploadingFile={isUploadingFile}
            onSubmit={handleSave}
            onCancel={handleCancel}
          />
        )}
        {!showForm && (
          <RespuestaDataView
            respuestaData={respuestaData}
            radicado={selectedRadicado}
            fechaRadicado={selectedFechaRadicado}
            requiereMedida={medidaChecked}
            isEditable={isEditable}
            onViewFile={handleViewFile}
          />
        )}
      </div>
    </div>
  );
}
