import { useState, useRef } from "react";
import {
  uploadFileToDocuments,
  generateDocumentFileName,
} from "../../../../utils/fileUpload";
import {
  openDocumentById,
  isValidDocumentId,
} from "../../../../utils/documentViewer";
import { apiCall, API_CONFIG } from "../../../../utils/api";
import CustomSelect from "../../../Common/Form/CustomSelect";

type FormulationCharges = {
  id: number;
  descargos: boolean | null;
  documento_id?: number | null;
};

type Props = {
  data: FormulationCharges | undefined;
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  etapaId: number;
  expedienteId: number;
  onDataUpdated?: () => void;
  isEditable?: boolean;
};

const MAX_FILE_SIZE = 10 * 1024 * 1024;

export default function FormulacionCargosData({
  data,
  setToast,
  etapaId,
  expedienteId,
  onDataUpdated,
  isEditable = true,
}: Props) {
  const [showForm, setShowForm] = useState(!data && isEditable);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [descargosValue, setDescargosValue] = useState<string>(
    data?.descargos === null ? "null" : data?.descargos?.toString() || "null",
  );
  const fileInputRef = useRef<HTMLInputElement>(null);

  const getDescargosLabel = (estado: boolean | null) => {
    if (estado === null) return "No Aplica";
    return estado ? "Sí" : "No";
  };

  const getDescargosBadgeClass = (estado: boolean | null) => {
    if (estado === null) return "badge-ghost";
    return estado ? "badge-success" : "badge-error";
  };

  const handleViewDocument = () => {
    if (
      data?.documento_id &&
      isValidDocumentId(data.documento_id)
    ) {
      openDocumentById(data.documento_id);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type !== "application/pdf") {
        setToast({
          id: Date.now(),
          message: "Solo se permiten archivos PDF",
          type: "error",
        });
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
        return;
      }

      if (file.size > MAX_FILE_SIZE) {
        setToast({
          id: Date.now(),
          message: "El archivo no debe superar los 10MB",
          type: "error",
        });
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
        return;
      }

      setSelectedFile(file);
    }
  };

  const handleDescargosChange = (value: string) => {
    setDescargosValue(value);

    if (value !== "true") {
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      let descargosBoolean: boolean | null = null;
      if (descargosValue === "true") descargosBoolean = true;
      else if (descargosValue === "false") descargosBoolean = false;
      else if (descargosValue === "null") descargosBoolean = null;

      if (
        descargosBoolean === true &&
        !selectedFile &&
        !data?.documento_id
      ) {
        setToast({
          id: Date.now(),
          message:
            "Debe adjuntar un documento PDF cuando los descargos son 'Sí'",
          type: "error",
        });
        setIsLoading(false);
        return;
      }

      // Documento vigente: el ya guardado, salvo que se suba uno nuevo.
      let documentoId: number | null | undefined = data?.documento_id ?? null;

      if (selectedFile) {
        const fileName = generateDocumentFileName(
          "DESCARGOS",
          `F-${etapaId}`,
          new Date().toISOString().split("T")[0],
        );
        documentoId = await uploadFileToDocuments(selectedFile, fileName);
      }

      const requestBody = {
        descargos: descargosBoolean,
        documento_id: documentoId,
      };

      let res;
      if (data?.id) {
        res = await apiCall(
          API_CONFIG.ENDPOINTS.FILE_FORMULATION_UPDATE(expedienteId),
          {
            method: "PUT",
            body: JSON.stringify(requestBody),
            headers: { "Content-Type": "application/json" },
          },
        );
      } else {
        res = await apiCall(API_CONFIG.ENDPOINTS.FILE_FORMULATION_CREATE(expedienteId), {
          method: "POST",
          body: JSON.stringify(requestBody),
          headers: { "Content-Type": "application/json" },
        });
      }

      if (res.ok) {
        setToast({
          id: Date.now(),
          message: data?.id
            ? "Información actualizada exitosamente"
            : "Información registrada exitosamente",
          type: "success",
        });
        setShowForm(false);
        setSelectedFile(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }

        if (onDataUpdated) {
          onDataUpdated();
        }
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al guardar",
          type: "error",
        });
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "Error al procesar la solicitud";

      setToast({
        id: Date.now(),
        message: errorMessage,
        type: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    if (data) {
      setShowForm(false);
      setSelectedFile(null);
      setDescargosValue(
        data?.descargos === null
          ? "null"
          : data?.descargos?.toString() || "null",
      );
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const showDocumentField = descargosValue === "true";
  const documentRequired =
    descargosValue === "true" && !data?.documento_id;

  return (
    <div className="card bg-base-100 shadow-md border border-base-300">
      <div className="card-body">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-warning/10 rounded-lg flex items-center justify-center">
              <svg
                className="w-5 h-5 text-warning"
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
            </div>
            <div>
              <h3 className="text-xl font-bold">Información de Formulación</h3>
              <p className="text-sm text-base-content/60">
                {data
                  ? "Información sobre descargos y documento"
                  : isEditable
                    ? "Registra información de formulación"
                    : "No hay información registrada"}
              </p>
            </div>
          </div>
          {!showForm && data && isEditable && (
            <button
              className="btn btn-ghost btn-sm gap-2 text-warning hover:bg-warning/10"
              onClick={() => setShowForm(true)}
              disabled={isLoading}
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

        {!showForm && data && (
          <div className="space-y-4">
            <div
              className={`grid grid-cols-1 ${
                data.descargos === true && data.documento_id
                  ? "md:grid-cols-2"
                  : ""
              } gap-4`}
            >
              {/* Estado de Descargos */}
              <div className="flex items-start gap-3">
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
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
                    Estado de Descargos
                  </p>
                  <span
                    className={`badge text-white ${getDescargosBadgeClass(
                      data.descargos,
                    )} badge-sm mt-1`}
                  >
                    {getDescargosLabel(data.descargos)}
                  </span>
                </div>
              </div>

              {/* Documento - Solo si descargos es "Sí" */}
              {data.descargos === true && (
                <div className="flex items-start">
                  <div className="flex-1">
                    {data.documento_id ? (
                      <button
                        onClick={handleViewDocument}
                        className="btn btn-success btn-sm gap-1 px-2 tooltip"
                        data-tip="Ver documento de descargos"
                      >
                        <svg
                          className="w-4 h-4 text-white"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" />
                        </svg>
                        <span className="text-xs font-medium text-white">
                          Documento Descargos
                        </span>
                      </button>
                    ) : (
                      <p className="text-sm text-base-content/60">
                        Sin documento
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {!showForm && !data && !isEditable && (
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
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-base-content/70 mb-2">
              Sin información registrada
            </h3>
            <p className="text-base-content/60">
              No hay información de formulación para este expediente
            </p>
          </div>
        )}

        {showForm && isEditable && (
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">
                  Estado de Descargos <span className="text-error">*</span>
                </span>
              </label>
              <CustomSelect
                hidePlaceholderOption
                value={descargosValue}
                onChange={handleDescargosChange}
                disabled={isLoading}
                options={[
                  { value: "true", label: "Sí" },
                  { value: "false", label: "No" },
                  { value: "null", label: "No Aplica" },
                ]}
              />
              <label className="label">
                <span className="label-text-alt text-base-content/60">
                  {descargosValue === "true"
                    ? "Se requiere adjuntar documento de descargos"
                    : "No es necesario adjuntar documento"}
                </span>
              </label>
            </div>

            {/* Campo de documento - Solo visible si descargos es "Sí" */}
            {showDocumentField && (
              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">
                    Documento de Descargos (PDF){" "}
                    {documentRequired ? (
                      <span className="text-error">*</span>
                    ) : (
                      data?.documento_id && (
                        <span className="text-xs text-base-content/50 ml-2">
                          (Opcional - Solo si desea reemplazar)
                        </span>
                      )
                    )}
                  </span>
                </label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="application/pdf"
                  className="file-input file-input-bordered w-full"
                  onChange={handleFileChange}
                  disabled={isLoading}
                  required={documentRequired}
                />
                <label className="label">
                  <span className="label-text-alt text-base-content/60">
                    Formato: PDF | Tamaño máximo: 10MB
                  </span>
                </label>
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
                    <span className="text-xs text-base-content/60">
                      ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                    </span>
                  </div>
                )}
                {data?.documento_id && !selectedFile && (
                  <p className="mt-2 text-xs text-base-content/60">
                    Archivo actual: Documento registrado
                  </p>
                )}
              </div>
            )}

            <div className="flex gap-3 justify-end pt-4 border-t border-base-300">
              {data && (
                <button
                  type="button"
                  onClick={handleCancel}
                  className="btn btn-outline"
                  disabled={isLoading}
                >
                  Cancelar
                </button>
              )}
              <button
                type="submit"
                className="btn btn-warning text-white gap-2"
                disabled={isLoading}
              >
                {isLoading ? (
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
                    {data ? "Guardar Cambios" : "Registrar Información"}
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
