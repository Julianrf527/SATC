import type { InvolucradoNotificacion } from "../../../types/sancionatorioApp";
import type { Involucrado } from "../../../types/involucradoApp";
import type { NotificacionFormApi } from "./useNotificacionForm";

type Props = {
  form: NotificacionFormApi;
  editingNotificacion: InvolucradoNotificacion | null;
  involucradosDisponibles: Involucrado[];
};

// Formatea el número de documento con DV para NITs
const formatDocumentNumber = (involucrado: Involucrado): string => {
  if (involucrado.tipo_documento === "NIT" && involucrado.digito_verificacion) {
    return `${involucrado.numero_documento}-${involucrado.digito_verificacion}`;
  }
  return involucrado.numero_documento.toString();
};

/**
 * Bloque del formulario correspondiente a la citación: involucrado, numerado,
 * fechas y documento de citación.
 */
export default function NotificacionCitacionFields({
  form,
  editingNotificacion,
  involucradosDisponibles,
}: Props) {
  const {
    notificacionForm,
    setNotificacionForm,
    errors,
    setErrors,
    selectedFileCitacion,
    isSubmitting,
    isUploadingFiles,
    isEditing,
    fileCitacionInputRef,
    handleFileCitacionChange,
    handleNumeradoChange,
  } = form;

  return (
    <>
      {/* Involucrado a Notificar - Solo en creación */}
      {!editingNotificacion && (
        <div className="form-control">
          <label className="label">
            <span className="label-text font-medium">
              Involucrado a Notificar
              <span className="text-error ml-1">*</span>
            </span>
          </label>
          <select
            value={notificacionForm.involucrado_id}
            onChange={(e) =>
              setNotificacionForm({
                ...notificacionForm,
                involucrado_id: Number(e.target.value),
              })
            }
            className={`select select-bordered w-full ${
              errors.involucrado_id ? "select-error" : "focus:select-success"
            }`}
            disabled={isSubmitting || isUploadingFiles}
          >
            <option value={0}>Seleccione un involucrado</option>
            {involucradosDisponibles.map((involucrado) => (
              <option key={involucrado.id} value={involucrado.id}>
                {involucrado.nombre} ({involucrado.tipo_documento}:{" "}
                {formatDocumentNumber(involucrado)})
              </option>
            ))}
          </select>
          {errors.involucrado_id && (
            <label className="label">
              <span className="label-text-alt text-error">
                {errors.involucrado_id}
              </span>
            </label>
          )}
        </div>
      )}

      {/* Numerado y Fecha Numerado */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="form-control">
          <label className="label">
            <span className="label-text font-medium">
              Numerado{" "}
              <span className="text-xs text-base-content/50">(4 dígitos)</span>
              <span className="text-error ml-1">*</span>
            </span>
          </label>
          <input
            type="text"
            value={notificacionForm.numerado}
            onChange={handleNumeradoChange}
            className={`input input-bordered w-full font-mono ${
              errors.numerado ? "input-error" : "focus:input-success"
            }`}
            placeholder="0001"
            maxLength={4}
            disabled={isSubmitting || isUploadingFiles}
          />
          {errors.numerado && (
            <label className="label">
              <span className="label-text-alt text-error">
                {errors.numerado}
              </span>
            </label>
          )}
        </div>

        <div className="form-control">
          <label className="label">
            <span className="label-text font-medium">
              Fecha Numerado
              <span className="text-error ml-1">*</span>
            </span>
          </label>
          <input
            type="date"
            value={notificacionForm.fecha_numerado}
            onChange={(e) => {
              setNotificacionForm({
                ...notificacionForm,
                fecha_numerado: e.target.value,
              });
              if (errors.fecha_numerado) {
                setErrors((prev) => ({ ...prev, fecha_numerado: "" }));
              }
            }}
            className={`input input-bordered w-full ${
              errors.fecha_numerado ? "input-error" : "focus:input-success"
            }`}
            max={new Date().toISOString().split("T")[0]}
            disabled={isSubmitting || isUploadingFiles}
          />
          {errors.fecha_numerado && (
            <label className="label">
              <span className="label-text-alt text-error">
                {errors.fecha_numerado}
              </span>
            </label>
          )}
        </div>
      </div>

      {/* Fecha Envío Citación y Fecha Constancia Citación */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="form-control">
          <label className="label">
            <span className="label-text font-medium">
              Fecha Envío Citación
              <span className="text-error ml-1">*</span>
            </span>
          </label>
          <input
            type="date"
            value={notificacionForm.fecha_envio_citacion}
            onChange={(e) => {
              setNotificacionForm({
                ...notificacionForm,
                fecha_envio_citacion: e.target.value,
              });
              if (errors.fecha_envio_citacion) {
                setErrors((prev) => ({
                  ...prev,
                  fecha_envio_citacion: "",
                }));
              }
            }}
            className={`input input-bordered w-full ${
              errors.fecha_envio_citacion
                ? "input-error"
                : "focus:input-success"
            }`}
            max={new Date().toISOString().split("T")[0]}
            disabled={isSubmitting || isUploadingFiles}
          />
          {errors.fecha_envio_citacion && (
            <label className="label">
              <span className="label-text-alt text-error">
                {errors.fecha_envio_citacion}
              </span>
            </label>
          )}
        </div>

        <div className="form-control">
          <label className="label">
            <span className="label-text font-medium">
              Fecha Constancia Citación
            </span>
          </label>
          <input
            type="date"
            value={notificacionForm.fecha_constancia_citacion}
            onChange={(e) =>
              setNotificacionForm({
                ...notificacionForm,
                fecha_constancia_citacion: e.target.value,
              })
            }
            className="input input-bordered w-full focus:input-success"
            max={new Date().toISOString().split("T")[0]}
            disabled={isSubmitting || isUploadingFiles}
          />
        </div>
      </div>

      {/* Documento Citación */}
      <div className="form-control">
        <label className="label">
          <span className="label-text font-medium">
            Documento Citación
            {!isEditing && <span className="text-error ml-1">*</span>}
            <span className="text-xs text-base-content/50 ml-2">
              (PDF - Máx. 10MB)
            </span>
          </span>
        </label>
        <input
          ref={fileCitacionInputRef}
          type="file"
          accept=".pdf,application/pdf"
          className={`file-input file-input-bordered w-full ${
            errors.file_citacion ? "file-input-error" : ""
          }`}
          onChange={handleFileCitacionChange}
          disabled={isSubmitting || isUploadingFiles}
        />
        {errors.file_citacion && (
          <label className="label">
            <span className="label-text-alt text-error">
              {errors.file_citacion}
            </span>
          </label>
        )}
        {selectedFileCitacion && !errors.file_citacion && (
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
                  d="M5 13l4 4L19 7"
                />
              </svg>
              {selectedFileCitacion.name}
            </span>
          </label>
        )}
        {isEditing &&
          !selectedFileCitacion &&
          editingNotificacion?.documento_citacion_id && (
            <label className="label">
              <span className="label-text-alt text-info">
                Opcional - Solo si desea reemplazar el documento actual
              </span>
            </label>
          )}
        {isEditing &&
          !selectedFileCitacion &&
          !editingNotificacion?.documento_citacion_id && (
            <label className="label">
              <span className="label-text-alt text-warning">
                ⚠️ No hay documento de citación cargado. Debe subir uno para
                habilitar la sección de notificación.
              </span>
            </label>
          )}
      </div>
    </>
  );
}
