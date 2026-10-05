import type { ChangeEvent, FormEvent, RefObject } from "react";
import CustomDateInput from "@shared/ui/form/CustomDateInput";
import type { RespuestaData } from "../../types";

type Props = {
  respuestaData: RespuestaData | null;
  radicado: string;
  onRadicadoChange: (value: string) => void;
  fechaRadicado: string;
  onFechaRadicadoChange: (value: string) => void;
  requiereMedida: boolean;
  onRequiereMedidaChange: (value: boolean) => void;
  selectedFile: File | null;
  onFileChange: (e: ChangeEvent<HTMLInputElement>) => void;
  fileInputRef: RefObject<HTMLInputElement | null>;
  isSubmitting: boolean;
  isUploadingFile: boolean;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
  onCancel: () => void;
};

/** Formulario de creación/edición de la etapa de respuesta. */
export default function RespuestaForm({
  respuestaData,
  radicado,
  onRadicadoChange,
  fechaRadicado,
  onFechaRadicadoChange,
  requiereMedida,
  onRequiereMedidaChange,
  selectedFile,
  onFileChange,
  fileInputRef,
  isSubmitting,
  isUploadingFile,
  onSubmit,
  onCancel,
}: Props) {
  return (
    <form onSubmit={onSubmit} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Radicado SIAF */}
        <div className="flex flex-col">
          <label className="label">
            <span className="text-sm text-base-content font-medium">Radicado SIAF</span>
          </label>
          <input
            type="text"
            name="radicado"
            value={radicado}
            onChange={(e) => onRadicadoChange(e.target.value)}
            className="input w-full font-mono"
            required
            disabled={isSubmitting || isUploadingFile}
            pattern="^\d{4}(IE|EE|ER)\d{4,5}$"
            title="Debe tener el formato: 4 números + IE o EE o ER + 4 o 5 números (ej: 2015IE5678)"
          ></input>
        </div>

        {/* Fecha Radicado SIAF */}
        <div className="flex flex-col">
          <label className="label">
            <span className="text-sm text-base-content font-medium">
              Fecha Radicado SIAF
            </span>
          </label>
          <CustomDateInput
            value={fechaRadicado}
            onChange={onFechaRadicadoChange}
            max={new Date().toISOString().split('T')[0]}
            disabled={isSubmitting || isUploadingFile}
          />
        </div>

        {/* Requiere Medida Preventiva */}
        <div className="flex flex-col">
          <label className="label">
            <span className="text-sm text-base-content font-medium">
              Requiere Medida Preventiva
            </span>
          </label>
          <div className="flex items-center h-10">
            <input
              type="checkbox"
              name="medida_preventiva"
              checked={requiereMedida}
              onChange={(e) => onRequiereMedidaChange(e.target.checked)}
              className="checkbox checkbox-info"
              disabled={isSubmitting || isUploadingFile}
            />
          </div>
        </div>
      </div>

      {/* Documento PDF */}
      <div className="flex flex-col">
        <label className="block text-sm font-medium text-base-content/70 mb-2">
          Documento PDF{" "}
          {!respuestaData && <span className="text-error">*</span>}
          {respuestaData && (
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
          onChange={onFileChange}
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
            onClick={onCancel}
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
  );
}
