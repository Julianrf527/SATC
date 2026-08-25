import { useEffect, useState, useRef } from "react";
import { apiCall, API_CONFIG } from "../../../../utils/api";
import type { RespuestaData } from "../../../../types/infraccionApp";
import {
  uploadFileToDocuments,
  generateDocumentFileName,
} from "../../../../utils/fileUpload";
import CustomDateInput from "../../../Common/Form/CustomDateInput";

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

  const handleRadicadoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSelectedRadicado(e.target.value);
  };
  const handleFechaRadicadoChange = (value: string) => {
    setSelectedFechaRadicado(value);
  };
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };
  const handleMedidaCheckedChange = (
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    setMedidaChecked(e.target.checked);
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
          const fileName = generateDocumentFileName(
            "Auto",
            selectedRadicado,
            selectedFechaRadicado,
          );
          documento_id = await uploadFileToDocuments(selectedFile, fileName);
        } catch (uploadError) {
          throw new Error(
            uploadError instanceof Error
              ? uploadError.message
              : "Error al subir el archivo a la aplicación de documentos",
          );
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

      let ENDPOINT;
      if (isCreatingStage) {
        ENDPOINT =
          API_CONFIG.ENDPOINTS.INFRACTION_CREATE_ANSWER_STAGE(expedienteId);
      } else {
        if (!respuestaData?.id) {
          setToast({
            id: Date.now(),
            type: "error",
            message: "No se encontró la respuesta para actualizar",
          });
          return;
        }
        ENDPOINT = API_CONFIG.ENDPOINTS.INFRACTION_PUT_ANSWER(respuestaData.id);
      }

      const result = await apiCall(ENDPOINT, {
        method: isCreatingStage ? "POST" : "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          radicado: respuestaDataCall.radicado,
          fecha_radicado: respuestaDataCall.fecha_radicado,
          documento_radicado_id: respuestaDataCall.documento_radicado_id,
          requiere_medida_preventiva:
            respuestaDataCall.requiere_medida_preventiva,
        }),
      });

      if (result.ok) {
        setToast({
          id: Date.now(),
          type: "success",
          message: isCreatingStage
            ? "Etapa respuesta creada correctamente"
            : "Etapa respuesta actualizada correctamente",
        });
        handleClose();
        // Re-consulta BD en el padre para confirmar persistencia
        onSaveSuccess?.();
      } else {
        const mensaje =
          result.status === 409
            ? (result.detail ?? "El radicado ya existe en otra respuesta")
            : "Error al guardar la respuesta";
        setToast({ id: Date.now(), type: "error", message: mensaje });
      }
    } catch (error) {
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
              className="btn btn-ghost btn-sm gap-2 text-info hover:bg-info/10"
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
          <form onSubmit={handleSave} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Radicado SIAF */}
              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">Radicado SIAF</span>
                </label>
                <input
                  type="text"
                  name="radicado"
                  value={selectedRadicado}
                  onChange={handleRadicadoChange}
                  className="input input-bordered w-full font-mono"
                  required
                  disabled={isSubmitting || isUploadingFile}
                  pattern="^\d{4}(IE|EE|ER)\d{4,5}$"
                  title="Debe tener el formato: 4 números + IE o EE o ER + 4 o 5 números (ej: 2015IE5678)"
                ></input>
              </div>

              {/* Fecha Radicado SIAF */}
              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">
                    Fecha Radicado SIAF
                  </span>
                </label>
                <CustomDateInput
                  value={selectedFechaRadicado}
                  onChange={handleFechaRadicadoChange}
                  max={new Date().toISOString().split('T')[0]}
                  disabled={isSubmitting || isUploadingFile}
                />
              </div>

              {/* Requiere Medida Preventiva */}
              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">
                    Requiere Medida Preventiva
                  </span>
                </label>
                <div className="flex items-center h-10">
                  <input
                    type="checkbox"
                    name="medida_preventiva"
                    checked={medidaChecked}
                    onChange={handleMedidaCheckedChange}
                    className="checkbox checkbox-info"
                    disabled={isSubmitting || isUploadingFile}
                  />
                </div>
              </div>
            </div>

            {/* Documento PDF */}
            <div className="form-control">
              <label className="block text-sm font-medium text-base-content/70 mb-2">
                Documento PDF{" "}
                {!respuestaData && <span className="text-error">*</span>}
                {respuestaData && (
                  <span className="text-xs text-base-content/50 ml-2">
                    (Opcional - Solo si desea reemplazar)
                  </span>
                )}
              </label>
              <input
                ref={fileInputRef}
                type="file"
                accept="application/pdf"
                className="file-input file-input-bordered w-full"
                onChange={handleFileChange}
                required={!respuestaData}
                disabled={isSubmitting || isUploadingFile}
              />
              {selectedFile && (
                <div className="mt-2 flex items-center gap-2 text-sm text-success">
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
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <span>{selectedFile.name}</span>
                </div>
              )}
              {!selectedFile && respuestaData && (
                <p className="mt-2 text-xs text-base-content/60">
                  Archivo actual: Documento registrado
                </p>
              )}
            </div>

            {/* Botones */}
            <div className="flex gap-3 justify-end pt-4 border-t border-base-300">
              {respuestaData && (
                <button
                  type="button"
                  onClick={handleCancel}
                  className="btn btn-outline"
                  disabled={isSubmitting || isUploadingFile}
                >
                  Cancelar
                </button>
              )}
              <button
                type="submit"
                className="btn btn-info text-white gap-2"
                disabled={isSubmitting || isUploadingFile}
              >
                {isSubmitting ? (
                  <>
                    <span className="loading loading-spinner loading-sm"></span>
                    Guardando...
                  </>
                ) : (
                  <>
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
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                    Registrar Respuesta
                  </>
                )}
              </button>
            </div>
          </form>
        )}
        {/* VISTA DE DATOS */}
        {!showForm && respuestaData && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="space-y-4">
              <div className="flex items-start gap-2">
                <div className="w-8 h-8 bg-base-200 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                  <svg
                    className="w-4 h-4 text-base-content/70"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
                    Radicado SIAF
                  </p>
                  <p className="text-sm font-semibold">{selectedRadicado}</p>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex items-start gap-2">
                <div className="w-8 h-8 bg-base-200 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                  <svg
                    className="w-4 h-4 text-base-content/70"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M8 7V3m8 4V3m-9 8h10m-12 9h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v11a2 2 0 002 2z"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
                    Fecha Radicado SIAF
                  </p>
                  <p className="text-sm font-semibold">
                    {selectedFechaRadicado
                      ? (() => { const [y, m, d] = selectedFechaRadicado.split("-"); return `${d}/${m}/${y}`; })()
                      : "—"}
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex items-start gap-2">
                <div className="w-8 h-8 bg-base-200 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                  <svg
                    className="w-4 h-4 text-base-content/70"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M8 7V3m8 4V3m-9 8h10m-12 9h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v11a2 2 0 002 2z"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
                    Requiere Medida Preventiva
                  </p>
                  <p className="text-sm font-semibold">
                    {medidaChecked ? "Sí" : "No"}
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <button
                onClick={handleViewFile}
                className="btn btn-success btn-sm gap-1 px-2 tooltip"
                data-tip="Ver documento PDF"
              >
                <svg
                  className="w-4 h-4 text-white"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M15.5,15.5L13,19L11.5,15.5L8,14L11.5,12.5L13,9L14.5,12.5L18,14L15.5,15.5M13,3.5L17.5,8H13V3.5Z" />
                </svg>
                <span className="text-xs font-medium text-white">
                  Documento SIAF
                </span>
              </button>
            </div>
          </div>
        )}

        {/* MENSAJE CUANDO NO HAY DATOS Y NO ES EDITABLE */}
        {!showForm && !respuestaData && !isEditable && (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-base-200 rounded-full flex items-center justify-center mb-4 mx-auto">
              <svg
                className="w-8 h-8 text-base-content/40"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-base-content/70 mb-2">
              Sin medida registrada
            </h3>
            <p className="text-base-content/60">
              No hay información de medida preventiva para este expediente
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
