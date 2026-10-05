import { useId } from "react";
import { Modal } from "@shared/ui";
import CustomSelect from "@shared/ui/form/CustomSelect";
import type { DocumentoAnexo, DocumentoAnexoPayload } from "../../types";
import Icono from "../comun/Icono";
import { ICONOS } from "../comun/iconos";
import { useDocumentoForm } from "./useDocumentoForm";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: DocumentoAnexoPayload) => Promise<{ ok: boolean; error?: string }>;
  editDocumento: DocumentoAnexo | null;
  tiposDocumento: string[];
};

/** Modal para crear / editar un documento anexo de etapa. */
export default function DocumentModal(props: Props) {
  const { isOpen, tiposDocumento } = props;
  const f = useDocumentoForm(props);
  const formId = useId();
  const opciones = [...tiposDocumento, "Otro"];

  return (
    <Modal
      isOpen={isOpen}
      onClose={f.handleClose}
      title={f.isEditing ? "Editar Documento" : "Nuevo Documento"}
      size="lg"
      footer={
        <>
          <button type="button" onClick={f.handleClose} className="btn btn-ghost" disabled={f.ocupado}>
            Cancelar
          </button>
          <button type="submit" form={formId} className="btn btn-success text-white" disabled={f.ocupado}>
            {f.isUploadingFile ? (
              <>
                <span className="loading loading-spinner loading-sm"></span>
                Subiendo archivo...
              </>
            ) : f.isSubmitting ? (
              <>
                <span className="loading loading-spinner loading-sm"></span>
                Guardando...
              </>
            ) : f.isEditing ? (
              "Actualizar"
            ) : (
              "Crear"
            )}
          </button>
        </>
      }
    >
      <form id={formId} onSubmit={f.handleSave} className="space-y-4 select-none">
        <div>
          <label className="block text-sm font-medium text-base-content/70 mb-1">
            Tipo de Documento <span className="text-error">*</span>
          </label>
          <CustomSelect
            error={!!f.errors.tipo}
            value={opciones.indexOf(f.tipoDocumento) + 1}
            onChange={(i) => f.handleTipoChange(i === 0 ? "" : opciones[i - 1])}
            placeholder="Seleccione un tipo"
            disabled={f.ocupado}
            options={opciones.map((tipo, i) => ({ value: i + 1, label: tipo }))}
          />
          {f.errors.tipo && <p className="text-error text-xs mt-1">{f.errors.tipo}</p>}
        </div>

        {/* Nombre personalizado (solo si es "Otro") */}
        {f.isOtroSelected && (
          <div>
            <label className="block text-sm font-medium text-base-content/70 mb-1">
              Nombre del Documento <span className="text-error">*</span>
            </label>
            <input
              type="text"
              className={`input w-full ${f.errors.nombre ? "input-error" : ""}`}
              placeholder="Ingrese un nombre diferente a los tipos existentes"
              value={f.nombrePersonalizado}
              onChange={f.handleNombrePersonalizadoChange}
              disabled={f.ocupado}
            />
            {f.errors.nombre ? (
              <p className="text-error text-xs mt-1">{f.errors.nombre}</p>
            ) : (
              <p className="text-xs text-base-content/60 mt-1">
                El nombre debe ser diferente a: {tiposDocumento.join(", ")}
              </p>
            )}
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-base-content/70 mb-1">
            Documento PDF {!f.isEditing && <span className="text-error">*</span>}
            {f.isEditing && (
              <span className="text-xs text-base-content/60 ml-2">
                (Opcional - Solo si desea reemplazar)
              </span>
            )}
          </label>
          <input
            ref={f.fileInputRef}
            type="file"
            accept="application/pdf"
            className={`file-input w-full ${f.errors.file ? "file-input-error" : ""}`}
            onChange={f.handleFileChange}
            disabled={f.ocupado}
          />
          {f.errors.file && <p className="text-error text-xs mt-1">{f.errors.file}</p>}
          {f.selectedFile && !f.errors.file && (
            <div className="mt-2 flex items-center gap-2 text-sm text-success">
              <Icono d={ICONOS.checkCirculo} />
              <span>{f.selectedFile.name}</span>
            </div>
          )}
          {f.isEditing && !f.selectedFile && !f.errors.file && (
            <p className="mt-2 text-xs text-base-content/60">Archivo actual: Documento registrado</p>
          )}
        </div>

        {f.errors.general && (
          <div className="alert alert-error">
            <Icono
              d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
              className="stroke-current shrink-0 h-6 w-6"
            />
            <span>{f.errors.general}</span>
          </div>
        )}
      </form>
    </Modal>
  );
}
