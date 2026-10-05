import { useState, useRef } from "react";
import { uploadFileToDocuments, generateDocumentFileName } from "@shared/lib/fileUpload";
import { openDocumentById, isValidDocumentId } from "@shared/lib/documentViewer";
import { apiCall, API_CONFIG } from "@shared/lib/api";
import CustomSelect from "@shared/ui/form/CustomSelect";
import type { FormulacionCargosInfo, SetToast } from "../../types";
import SeccionDatos from "../comun/SeccionDatos";
import InfoItem from "../comun/InfoItem";
import SinInformacion from "../comun/SinInformacion";
import AccionesFormulario from "../comun/AccionesFormulario";
import Icono from "../comun/Icono";
import { ICONOS, PDF_RELLENO_20 } from "../comun/iconos";

type Props = {
  data: FormulacionCargosInfo | undefined;
  setToast: SetToast;
  etapaId: number;
  expedienteId: number;
  onDataUpdated?: () => void;
  isEditable?: boolean;
};

const MAX_FILE_SIZE = 10 * 1024 * 1024;

const descargosAValor = (d: boolean | null | undefined) =>
  d === null ? "null" : d?.toString() || "null";

const descargosLabel = (estado: boolean | null) =>
  estado === null ? "No Aplica" : estado ? "Sí" : "No";
const descargosBadge = (estado: boolean | null) =>
  estado === null ? "badge-ghost" : estado ? "badge-success" : "badge-error";

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
  const [descargosValue, setDescargosValue] = useState<string>(descargosAValor(data?.descargos));
  const fileInputRef = useRef<HTMLInputElement>(null);

  const limpiarArchivo = () => {
    setSelectedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const toastError = (message: string) => setToast({ id: Date.now(), message, type: "error" });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.type !== "application/pdf") {
      toastError("Solo se permiten archivos PDF");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      toastError("El archivo no debe superar los 10MB");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }
    setSelectedFile(file);
  };

  const handleDescargosChange = (value: string) => {
    setDescargosValue(value);
    if (value !== "true") limpiarArchivo();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const descargos: boolean | null =
        descargosValue === "true" ? true : descargosValue === "false" ? false : null;

      if (descargos === true && !selectedFile && !data?.documento_id) {
        toastError("Debe adjuntar un documento PDF cuando los descargos son 'Sí'");
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

      // La etapa ya existe ("Crear Etapa" hace el POST): los datos siempre se guardan con PUT.
      const res = await apiCall(API_CONFIG.ENDPOINTS.FILE_FORMULATION_UPDATE(expedienteId), {
        method: "PUT",
        body: JSON.stringify({ descargos, documento_id: documentoId }),
        headers: { "Content-Type": "application/json" },
      });

      if (res.ok) {
        setToast({
          id: Date.now(),
          message: data?.id
            ? "Información actualizada exitosamente"
            : "Información registrada exitosamente",
          type: "success",
        });
        setShowForm(false);
        limpiarArchivo();
        onDataUpdated?.();
      } else {
        toastError(res.detail || "Error al guardar");
      }
    } catch (error) {
      toastError(error instanceof Error ? error.message : "Error al procesar la solicitud");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    if (!data) return;
    setShowForm(false);
    setDescargosValue(descargosAValor(data.descargos));
    limpiarArchivo();
  };

  const documentRequired = descargosValue === "true" && !data?.documento_id;

  return (
    <SeccionDatos
      titulo="Información de Formulación"
      icono={ICONOS.documento}
      tono="warning"
      subtitulo={
        data
          ? "Información sobre descargos y documento"
          : isEditable
            ? "Registra información de formulación"
            : "No hay información registrada"
      }
      onEditar={!showForm && data && isEditable ? () => setShowForm(true) : undefined}
      deshabilitado={isLoading}
    >
      {!showForm && data && (
        <div className="space-y-4">
          <div
            className={`grid grid-cols-1 ${
              data.descargos === true && data.documento_id ? "md:grid-cols-2" : ""
            } gap-4`}
          >
            <InfoItem icono={ICONOS.checkCirculo} etiqueta="Estado de Descargos">
              <span className={`badge text-white ${descargosBadge(data.descargos)} badge-sm mt-1`}>
                {descargosLabel(data.descargos)}
              </span>
            </InfoItem>

            {/* Documento - Solo si descargos es "Sí" */}
            {data.descargos === true && (
              <div className="flex items-start">
                <div className="flex-1">
                  {data.documento_id ? (
                    <button
                      onClick={() => {
                        if (data.documento_id && isValidDocumentId(data.documento_id)) {
                          openDocumentById(data.documento_id);
                        }
                      }}
                      className="btn btn-success btn-sm gap-1 px-2 tooltip"
                      data-tip="Ver documento de descargos"
                    >
                      <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                        <path d={PDF_RELLENO_20} />
                      </svg>
                      <span className="text-xs font-medium text-white">Documento Descargos</span>
                    </button>
                  ) : (
                    <p className="text-sm text-base-content/60">Sin documento</p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {!showForm && !data && !isEditable && (
        <SinInformacion
          icono={ICONOS.documento}
          titulo="Sin información registrada"
          texto="No hay información de formulación para este expediente"
        />
      )}

      {showForm && isEditable && (
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="flex flex-col">
            <label className="label">
              <span className="text-sm text-base-content font-medium">
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
              <span className="text-xs text-base-content/60">
                {descargosValue === "true"
                  ? "Se requiere adjuntar documento de descargos"
                  : "No es necesario adjuntar documento"}
              </span>
            </label>
          </div>

          {/* Campo de documento - Solo visible si descargos es "Sí" */}
          {descargosValue === "true" && (
            <div className="flex flex-col">
              <label className="label">
                <span className="text-sm text-base-content font-medium">
                  Documento de Descargos (PDF){" "}
                  {documentRequired ? (
                    <span className="text-error">*</span>
                  ) : (
                    data?.documento_id && (
                      <span className="text-xs text-base-content/60 ml-2">
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
                className="file-input w-full"
                onChange={handleFileChange}
                disabled={isLoading}
                required={documentRequired}
              />
              <label className="label">
                <span className="text-xs text-base-content/60">
                  Formato: PDF | Tamaño máximo: 10MB
                </span>
              </label>
              {selectedFile && (
                <div className="mt-2 flex items-center gap-2 text-sm text-success">
                  <Icono d={ICONOS.checkCirculo} />
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

          <AccionesFormulario
            onCancelar={data ? handleCancel : undefined}
            textoGuardar={data ? "Guardar Cambios" : "Registrar Información"}
            tono="warning"
            guardando={isLoading}
          />
        </form>
      )}
    </SeccionDatos>
  );
}
