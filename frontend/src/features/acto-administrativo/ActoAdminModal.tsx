import { useState, useEffect, useRef } from "react";
import { Modal } from "@shared/ui";
import type { ActoAdministrativo } from "@shared/types/sancionatorio";
import type { ActoAdminFormData, ActoAdminSaveResult } from "./actoAdminConfig";
import CustomSelect from "@shared/ui/form/CustomSelect";
import CustomDateInput from "@shared/ui/form/CustomDateInput";
import {
  uploadFileToDocuments,
  generateDocumentFileName,
} from "@shared/lib/fileUpload";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: ActoAdminFormData) => Promise<ActoAdminSaveResult>;
  editActoAdmin: ActoAdministrativo | null;
};

export default function ActoAdminModal({
  isOpen,
  onClose,
  onSave,
  editActoAdmin,
}: Props) {
  const [tipoActo, setTipoActo] = useState<"AUTO" | "RES">("AUTO");
  const [numerado, setNumerado] = useState("");
  const [fechaNumerado, setFechaNumerado] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [errorGeneral, setErrorGeneral] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setErrorGeneral("");
      if (editActoAdmin) {
        setTipoActo(editActoAdmin.tipo_acto as "AUTO" | "RES");
        setNumerado(String(editActoAdmin.numerado).padStart(4, "0"));
        // Convertir fecha al formato yyyy-MM-dd para el input date
        const fechaFormateada =
          editActoAdmin.fecha_numerado?.split(" ")[0] ||
          editActoAdmin.fecha_numerado;
        setFechaNumerado(fechaFormateada);
        setSelectedFile(null);
      } else {
        setTipoActo("AUTO");
        setNumerado("");
        setFechaNumerado("");
        setSelectedFile(null);
      }
      setIsSubmitting(false);
    }
  }, [isOpen, editActoAdmin]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleNumeradoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.toUpperCase();
    if (value.length <= 4) {
      setNumerado(value);
    }
  };

  const handleSave = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErrorGeneral("");
    setIsSubmitting(true);

    try {
      let documento_acto_id: number | undefined;

      // Paso 1: Si hay archivo seleccionado, subirlo a app-docs primero
      if (selectedFile) {
        setIsUploadingFile(true);

        try {
          const fileName = generateDocumentFileName(
            tipoActo,
            numerado,
            fechaNumerado,
          );
          documento_acto_id = await uploadFileToDocuments(
            selectedFile,
            fileName,
          );
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

      // Paso 2: Enviar datos al endpoint de sancionatoria
      const actoData = {
        tipo_acto: tipoActo,
        numerado: numerado,
        fecha_numerado: fechaNumerado,
        ...(documento_acto_id && { documento_acto_id }),
        radicado_expediente: "", // Se agregará en el componente padre
        etapa_id: 0, // Se agregará en el componente padre
        nivel_auxiliar: null, // Se agregará en el componente padre si es necesario
      };

      const result = await onSave(actoData);

      if (result.ok) {
        handleClose();
      } else {
        setErrorGeneral(
          result.error || "Error al guardar el acto administrativo",
        );
      }
    } catch (error) {
      setErrorGeneral(
        error instanceof Error
          ? error.message
          : "Error inesperado al guardar el acto administrativo",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setTipoActo("AUTO");
    setNumerado("");
    setFechaNumerado("");
    setSelectedFile(null);
    setErrorGeneral("");
    setIsSubmitting(false);
    setIsUploadingFile(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    onClose();
  };

  const busy = isSubmitting || isUploadingFile;

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      size="xl"
      showCloseButton={false}
      closeOnEsc={!busy}
      closeOnBackdrop={!busy}
      title={
        editActoAdmin
          ? "Editar Acto Administrativo"
          : "Nuevo Acto Administrativo"
      }
    >
      <form onSubmit={handleSave} className="space-y-4 select-none">
        <div className="flex gap-4">
          <div className="w-1/3">
            <label className="block text-sm font-medium text-base-content/70 mb-1">
              Tipo de Acto <span className="text-error">*</span>
            </label>
            <CustomSelect
              hidePlaceholderOption
              value={tipoActo === "AUTO" ? 0 : 1}
              onChange={(i) => setTipoActo(i === 0 ? "AUTO" : "RES")}
              disabled={busy}
              options={[
                { value: 0, label: "AUTO" },
                { value: 1, label: "RES" },
              ]}
            />
          </div>
          <div className="w-2/3">
            <label className="block text-sm font-medium text-base-content/70 mb-1">
              Numerado <span className="text-error">*</span>
              <span className="text-xs text-base-content/60 ml-2">
                (Ej: 1234)
              </span>
            </label>
            <input
              type="number"
              className="input w-full font-mono"
              placeholder="1234"
              value={numerado}
              onChange={handleNumeradoChange}
              maxLength={4}
              minLength={4}
              required
              disabled={busy}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-base-content/70 mb-1">
            Fecha de Numerado <span className="text-error">*</span>
          </label>
          <CustomDateInput
            value={fechaNumerado}
            onChange={setFechaNumerado}
            max={new Date().toISOString().split('T')[0]}
            disabled={busy}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-base-content/70 mb-1">
            Documento PDF{" "}
            {!editActoAdmin && <span className="text-error">*</span>}
            {editActoAdmin && (
              <span className="text-xs text-base-content/60 ml-2">
                (Opcional - Solo si desea reemplazar)
              </span>
            )}
          </label>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            className="file-input w-full"
            onChange={handleFileChange}
            required={!editActoAdmin}
            disabled={busy}
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
          {editActoAdmin && !selectedFile && (
            <p className="mt-2 text-xs text-base-content/60">
              Archivo actual: Documento registrado
            </p>
          )}
        </div>

        {errorGeneral && (
          <div className="alert alert-error">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="stroke-current shrink-0 h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span>{errorGeneral}</span>
          </div>
        )}

        <div className="flex justify-end space-x-2 mt-6">
          <button
            type="button"
            onClick={handleClose}
            className="btn btn-ghost"
            disabled={busy}
          >
            Cancelar
          </button>
          <button
            type="submit"
            className="btn btn-success text-white"
            disabled={busy}
          >
            {isUploadingFile ? (
              <>
                <span className="loading loading-spinner loading-sm"></span>
                Subiendo archivo...
              </>
            ) : isSubmitting ? (
              <>
                <span className="loading loading-spinner loading-sm"></span>
                Guardando...
              </>
            ) : editActoAdmin ? (
              "Actualizar"
            ) : (
              "Crear"
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
}
