import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import type { ActoAdminData } from "../../../../types";
import {
  uploadFileToDocuments,
  generateDocumentFileName,
} from "../../../../utils/fileUpload";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: {
    tipo_acto: string;
    numerado: string;
    fecha_numerado: string;
    documento_acto_id?: number;
    radicado_expediente: string;
    etapa_id: number;
    nivel_auxiliar?: boolean | null;
  }) => Promise<{ ok: boolean; error?: string }>;
  editActoAdmin: ActoAdminData | null;
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
  const [theme, setTheme] = useState<string>("emerald");
  const [errorGeneral, setErrorGeneral] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const updateTheme = () => {
      const currentTheme =
        document.querySelector("[data-theme]")?.getAttribute("data-theme") ||
        "emerald";
      setTheme(currentTheme);
    };

    updateTheme();
    const observer = new MutationObserver(updateTheme);
    const targetNode = document.querySelector("[data-theme]");

    if (targetNode) {
      observer.observe(targetNode, {
        attributes: true,
        attributeFilter: ["data-theme"],
      });
    }

    return () => observer.disconnect();
  }, []);

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

  if (!isOpen) return null;

  const modalContent = (
    <div
      data-theme={theme}
      className="fixed inset-0 z-[999999] flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={handleClose}
    >
      <div
        className="bg-base-100 rounded-lg p-6 w-full max-w-xl mx-4 shadow-2xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="font-bold text-lg mb-4 text-base-content">
          {editActoAdmin
            ? "Editar Acto Administrativo"
            : "Nuevo Acto Administrativo"}
        </h3>

        <form onSubmit={handleSave} className="space-y-4 select-none">
          <div className="flex gap-4">
            <div className="w-1/3">
              <label className="block text-sm font-medium text-base-content/70 mb-1">
                Tipo de Acto <span className="text-error">*</span>
              </label>
              <select
                className="select select-bordered w-full"
                required
                value={tipoActo}
                onChange={(e) => setTipoActo(e.target.value as "AUTO" | "RES")}
                disabled={isSubmitting || isUploadingFile}
              >
                <option value="AUTO">AUTO</option>
                <option value="RES">RES</option>
              </select>
            </div>
            <div className="w-2/3">
              <label className="block text-sm font-medium text-base-content/70 mb-1">
                Numerado <span className="text-error">*</span>
                <span className="text-xs text-base-content/50 ml-2">
                  (Ej: 1234)
                </span>
              </label>
              <input
                type="number"
                className="input input-bordered w-full font-mono"
                placeholder="1234"
                value={numerado}
                onChange={handleNumeradoChange}
                maxLength={4}
                minLength={4}
                required
                disabled={isSubmitting || isUploadingFile}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-base-content/70 mb-1">
              Fecha de Numerado <span className="text-error">*</span>
            </label>
            <input
              type="date"
              className="input input-bordered w-full"
              value={fechaNumerado}
              onChange={(e) => setFechaNumerado(e.target.value)}
              required
              disabled={isSubmitting || isUploadingFile}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-base-content/70 mb-1">
              Documento PDF{" "}
              {!editActoAdmin && <span className="text-error">*</span>}
              {editActoAdmin && (
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
              required={!editActoAdmin}
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
              disabled={isSubmitting || isUploadingFile}
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="btn btn-success text-white"
              disabled={isSubmitting || isUploadingFile}
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
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
