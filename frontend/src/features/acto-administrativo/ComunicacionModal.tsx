import { API_CONFIG } from "@shared/lib/api";
import { Modal } from "@shared/ui";
import CustomDateInput from "@shared/ui/form/CustomDateInput";
import type { ComunicacionData } from "./actoAdminConfig";
import { useComunicacionForm } from "./useComunicacionForm";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  expedienteId: number;
  actoAdminId: number;
  editComunicacion?: ComunicacionData | null;
  onSuccess?: (comunicacionData: ComunicacionData) => void;
  endpoints?: {
    create: string;
    update: (comunicacionId: number) => string;
  };
};

const DEFAULT_COMUNICACION_ENDPOINTS = {
  create: API_CONFIG.ENDPOINTS.FILE_COMUNICACION,
  update: API_CONFIG.ENDPOINTS.FILE_COMUNICACION_UPDATE,
};

export default function ComunicacionModal({
  isOpen,
  onClose,
  expedienteId,
  actoAdminId,
  editComunicacion,
  onSuccess,
  endpoints,
}: Props) {
  const {
    numerado,
    fechaNumerado,
    fechaEnvio,
    selectedFile,
    errors,
    isSubmitting,
    isUploadingFile,
    isEditing,
    fileInputRef,
    handleFileChange,
    handleNumeradoChange,
    handleFechaNumeradoChange,
    handleFechaEnvioChange,
    handleSave,
    handleClose,
  } = useComunicacionForm({
    isOpen,
    onClose,
    expedienteId,
    actoAdminId,
    editComunicacion,
    onSuccess,
    endpoints: endpoints ?? DEFAULT_COMUNICACION_ENDPOINTS,
  });

  const busy = isSubmitting || isUploadingFile;

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      size="xl"
      showCloseButton={false}
      closeOnEsc={!busy}
      closeOnBackdrop={!busy}
      title={isEditing ? "Editar Comunicación" : "Nueva Comunicación"}
    >
      <form onSubmit={handleSave} className="space-y-4 select-none">
        {/* Numerado */}
        <div>
          <label className="block text-sm font-medium text-base-content/70 mb-1">
            Numerado <span className="text-error">*</span>
            <span className="text-xs text-base-content/60 ml-2">
              (4 dígitos)
            </span>
          </label>
          <input
            type="text"
            className={`input w-full font-mono ${
 errors.numerado ? "input-error" : ""
 }`}
            placeholder="0001"
            value={numerado}
            onChange={handleNumeradoChange}
            maxLength={4}
            disabled={busy}
          />
          {errors.numerado && (
            <p className="text-error text-xs mt-1">{errors.numerado}</p>
          )}
        </div>

        {/* Fecha de Numeración y Fecha de Envío */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-base-content/70 mb-1">
              Fecha de Numeración <span className="text-error">*</span>
            </label>
            <CustomDateInput
              error={!!errors.fecha_numerado}
              value={fechaNumerado}
              onChange={handleFechaNumeradoChange}
              max={new Date().toISOString().split('T')[0]}
              disabled={busy}
            />
            {errors.fecha_numerado && (
              <p className="text-error text-xs mt-1">{errors.fecha_numerado}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-base-content/70 mb-1">
              Fecha de Envío <span className="text-error">*</span>
            </label>
            <CustomDateInput
              error={!!errors.fecha_envio}
              value={fechaEnvio}
              onChange={handleFechaEnvioChange}
              max={new Date().toISOString().split('T')[0]}
              disabled={busy}
            />
            {errors.fecha_envio && (
              <p className="text-error text-xs mt-1">{errors.fecha_envio}</p>
            )}
          </div>
        </div>

        {/* Archivo */}
        <div>
          <label className="block text-sm font-medium text-base-content/70 mb-1">
            Documento {!isEditing && <span className="text-error">*</span>}
            {isEditing && (
              <span className="text-xs text-base-content/60 ml-2">
                (Opcional - Solo si desea reemplazar)
              </span>
            )}
            <span className="text-xs text-base-content/60 ml-2">
              (PDF, JPG, PNG - Máx. 10MB)
            </span>
          </label>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,image/jpeg,image/png,application/pdf"
            className={`file-input w-full ${
 errors.file ? "file-input-error" : ""
 }`}
            onChange={handleFileChange}
            disabled={busy}
          />
          {errors.file && (
            <p className="text-error text-xs mt-1">{errors.file}</p>
          )}
          {selectedFile && !errors.file && (
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
          {isEditing && !selectedFile && !errors.file && (
            <p className="mt-2 text-xs text-base-content/60">
              Archivo actual: Documento registrado
            </p>
          )}
        </div>

        {/* Error general */}
        {errors.general && (
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
            <span>{errors.general}</span>
          </div>
        )}

        {/* Botones */}
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
            ) : isEditing ? (
              "Actualizar"
            ) : (
              "Agregar"
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
}
