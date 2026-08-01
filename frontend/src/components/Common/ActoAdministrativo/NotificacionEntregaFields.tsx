import type {
  InvolucradoNotificacion,
  TipoNotificacion,
} from "../../../types/sancionatorioApp";
import type { NotificacionFormApi } from "./useNotificacionForm";

type Props = {
  form: NotificacionFormApi;
  editingNotificacion: InvolucradoNotificacion | null;
  tiposNotificacion: TipoNotificacion[];
  /** Documento de citación ya cargado o recién seleccionado. */
  hasDocumentoCitacion: number | File | null | undefined | boolean;
};

/**
 * Bloque del formulario correspondiente a la entrega de la notificación:
 * notificación exitosa, tipo y documento de notificación.
 */
export default function NotificacionEntregaFields({
  form,
  editingNotificacion,
  tiposNotificacion,
  hasDocumentoCitacion,
}: Props) {
  const {
    notificacionForm,
    setNotificacionForm,
    errors,
    setErrors,
    selectedFile,
    selectedFileCitacion,
    isSubmitting,
    isEditing,
    fileInputRef,
    handleFileChange,
  } = form;

  return (
    <>
      {/* Separador visual */}
      {(editingNotificacion?.documento_citacion_id ||
        selectedFileCitacion ||
        !isEditing) && (
        <div className="divider text-sm text-base-content/50">
          Información de Notificación
        </div>
      )}

      {/* Citación Exitosa y Tipo Notificación */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="form-control">
          <label className="label">
            <span className="label-text font-medium">Notificación Exitosa</span>
          </label>
          <label
            className={`flex items-center h-12 px-4 rounded-lg border-2 ${
              !hasDocumentoCitacion ||
              !notificacionForm.fecha_constancia_citacion
                ? "opacity-50 cursor-not-allowed bg-base-200 border-base-300"
                : notificacionForm.notificacion_exitosa
                  ? "border-success bg-success/5 cursor-pointer"
                  : "border-base-300 hover:border-success/30 hover:bg-success/5 cursor-pointer"
            }`}
          >
            <input
              type="checkbox"
              checked={notificacionForm.notificacion_exitosa}
              onChange={(e) =>
                setNotificacionForm({
                  ...notificacionForm,
                  notificacion_exitosa: e.target.checked,
                })
              }
              className="checkbox checkbox-success"
              disabled={
                !hasDocumentoCitacion ||
                !notificacionForm.fecha_constancia_citacion ||
                isSubmitting
              }
            />
            <span className="ml-3 text-sm font-medium">
              {!hasDocumentoCitacion
                ? "Requiere documento de citación"
                : !notificacionForm.fecha_constancia_citacion
                  ? "Requiere fecha de constancia"
                  : "Notificación entregada"}
            </span>
          </label>
        </div>

        <div className="form-control">
          <label className="label">
            <span className="label-text font-medium">
              Tipo Notificación
              {notificacionForm.notificacion_exitosa && (
                <span className="text-error ml-1">*</span>
              )}
            </span>
          </label>
          <div className="relative">
            <select
              value={notificacionForm.tipo_notificacion_id}
              onChange={(e) => {
                setNotificacionForm({
                  ...notificacionForm,
                  tipo_notificacion_id: Number(e.target.value),
                });
                if (errors.tipo_notificacion_id) {
                  setErrors((prev) => ({
                    ...prev,
                    tipo_notificacion_id: "",
                  }));
                }
              }}
              className={`select select-bordered w-full h-12 ${
                errors.tipo_notificacion_id
                  ? "select-error border-2"
                  : notificacionForm.tipo_notificacion_id !== 0
                    ? "border-2 border-success"
                    : "focus:select-success"
              } ${
                !hasDocumentoCitacion || !notificacionForm.notificacion_exitosa
                  ? "opacity-50 cursor-not-allowed"
                  : ""
              }`}
              disabled={
                !hasDocumentoCitacion ||
                !notificacionForm.notificacion_exitosa ||
                isSubmitting
              }
            >
              <option value={0}>
                {!hasDocumentoCitacion
                  ? "Requiere documento de citación"
                  : !notificacionForm.notificacion_exitosa
                    ? "Marque citación exitosa primero"
                    : "Seleccione un tipo"}
              </option>
              {tiposNotificacion.map((tipo) => (
                <option key={tipo.id} value={tipo.id}>
                  {tipo.nombre}
                </option>
              ))}
            </select>
          </div>
          {errors.tipo_notificacion_id && (
            <label className="label">
              <span className="label-text-alt text-error">
                {errors.tipo_notificacion_id}
              </span>
            </label>
          )}
        </div>
      </div>

      {/* Documento Notificación */}
      <div className="form-control">
        <label className="label">
          <span className="label-text font-medium">
            Documento Notificación
            {notificacionForm.notificacion_exitosa && (
              <span className="text-error ml-1">*</span>
            )}
            <span className="text-xs text-base-content/50 ml-2">
              (PDF - Máx. 10MB)
            </span>
          </span>
        </label>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          className={`file-input file-input-bordered w-full ${
            errors.file ? "file-input-error" : ""
          } ${!hasDocumentoCitacion ? "opacity-50 cursor-not-allowed" : ""}`}
          onChange={handleFileChange}
          disabled={!notificacionForm.notificacion_exitosa || isSubmitting}
        />
        {errors.file && (
          <label className="label">
            <span className="label-text-alt text-error">{errors.file}</span>
          </label>
        )}
        {selectedFile && !errors.file && (
          <label className="label">
            <span className="label-text-alt text-success flex items-center gap-1">
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
              {selectedFile.name}
            </span>
          </label>
        )}
        {isEditing && !selectedFile && !errors.file && (
          <label className="label">
            <span className="label-text-alt text-base-content/60">
              {notificacionForm.notificacion_exitosa &&
              !editingNotificacion?.documento_notificacion_id
                ? "Debe cargar un documento de notificación"
                : "Opcional - Solo si desea reemplazar el documento"}
            </span>
          </label>
        )}
      </div>
    </>
  );
}
