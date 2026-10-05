import type { InvolucradoNotificacion } from "@shared/types/sancionatorio";
import type { Involucrado } from "@shared/types/involucrado";
import type { NotificacionFormApi } from "./useNotificacionForm";
import CustomSelect from "@shared/ui/form/CustomSelect";
import CustomDateInput from "@shared/ui/form/CustomDateInput";

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
        <div className="flex flex-col">
          <label className="label">
            <span className="text-sm text-base-content font-medium">
              Involucrado a Notificar
              <span className="text-error ml-1">*</span>
            </span>
          </label>
          <CustomSelect
            value={notificacionForm.involucrado_id}
            onChange={(v) =>
              setNotificacionForm({
                ...notificacionForm,
                involucrado_id: v,
              })
            }
            placeholder="Seleccione un involucrado"
            error={!!errors.involucrado_id}
            disabled={isSubmitting || isUploadingFiles}
            options={involucradosDisponibles.map((involucrado) => ({
              value: involucrado.id,
              label: `${involucrado.nombre} (${involucrado.tipo_documento}: ${formatDocumentNumber(involucrado)})`,
            }))}
          />
          {errors.involucrado_id && (
            <label className="label">
              <span className="text-xs text-error">
                {errors.involucrado_id}
              </span>
            </label>
          )}
        </div>
      )}

      {/* Numerado y Fecha Numerado */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="flex flex-col">
          <label className="label">
            <span className="text-sm text-base-content font-medium">
              Numerado{" "}
              <span className="text-xs text-base-content/60">(4 dígitos)</span>
              <span className="text-error ml-1">*</span>
            </span>
          </label>
          <input
            type="text"
            value={notificacionForm.numerado}
            onChange={handleNumeradoChange}
            className={`input w-full font-mono ${
 errors.numerado ? "input-error" : "focus:input-success"
 }`}
            placeholder="0001"
            maxLength={4}
            disabled={isSubmitting || isUploadingFiles}
          />
          {errors.numerado && (
            <label className="label">
              <span className="text-xs text-error">
                {errors.numerado}
              </span>
            </label>
          )}
        </div>

        <div className="flex flex-col">
          <label className="label">
            <span className="text-sm text-base-content font-medium">
              Fecha Numerado
              <span className="text-error ml-1">*</span>
            </span>
          </label>
          <CustomDateInput
            value={notificacionForm.fecha_numerado}
            onChange={(v) => {
              setNotificacionForm({
                ...notificacionForm,
                fecha_numerado: v,
              });
              if (errors.fecha_numerado) {
                setErrors((prev) => ({ ...prev, fecha_numerado: "" }));
              }
            }}
            error={!!errors.fecha_numerado}
            max={new Date().toISOString().split("T")[0]}
            disabled={isSubmitting || isUploadingFiles}
          />
          {errors.fecha_numerado && (
            <label className="label">
              <span className="text-xs text-error">
                {errors.fecha_numerado}
              </span>
            </label>
          )}
        </div>
      </div>

      {/* Fecha Envío Citación y Fecha Constancia Citación */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="flex flex-col">
          <label className="label">
            <span className="text-sm text-base-content font-medium">
              Fecha Envío Citación
              <span className="text-error ml-1">*</span>
            </span>
          </label>
          <CustomDateInput
            value={notificacionForm.fecha_envio_citacion}
            onChange={(v) => {
              setNotificacionForm({
                ...notificacionForm,
                fecha_envio_citacion: v,
              });
              if (errors.fecha_envio_citacion) {
                setErrors((prev) => ({
                  ...prev,
                  fecha_envio_citacion: "",
                }));
              }
            }}
            error={!!errors.fecha_envio_citacion}
            max={new Date().toISOString().split("T")[0]}
            disabled={isSubmitting || isUploadingFiles}
          />
          {errors.fecha_envio_citacion && (
            <label className="label">
              <span className="text-xs text-error">
                {errors.fecha_envio_citacion}
              </span>
            </label>
          )}
        </div>

        <div className="flex flex-col">
          <label className="label">
            <span className="text-sm text-base-content font-medium">
              Fecha Constancia Citación
            </span>
          </label>
          <CustomDateInput
            value={notificacionForm.fecha_constancia_citacion}
            onChange={(v) =>
              setNotificacionForm({
                ...notificacionForm,
                fecha_constancia_citacion: v,
              })
            }
            max={new Date().toISOString().split("T")[0]}
            disabled={isSubmitting || isUploadingFiles}
          />
        </div>
      </div>

      {/* Documento Citación */}
      <div className="flex flex-col">
        <label className="label">
          <span className="text-sm text-base-content font-medium">
            Documento Citación
            {!isEditing && <span className="text-error ml-1">*</span>}
            <span className="text-xs text-base-content/60 ml-2">
              (PDF - Máx. 10MB)
            </span>
          </span>
        </label>
        <input
          ref={fileCitacionInputRef}
          type="file"
          accept=".pdf,application/pdf"
          className={`file-input w-full ${
 errors.file_citacion ? "file-input-error" : ""
 }`}
          onChange={handleFileCitacionChange}
          disabled={isSubmitting || isUploadingFiles}
        />
        {errors.file_citacion && (
          <label className="label">
            <span className="text-xs text-error">
              {errors.file_citacion}
            </span>
          </label>
        )}
        {selectedFileCitacion && !errors.file_citacion && (
          <label className="label">
            <span className="text-xs text-success flex items-center gap-1">
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
              <span className="text-xs text-tono-info">
                Opcional - Solo si desea reemplazar el documento actual
              </span>
            </label>
          )}
        {isEditing &&
          !selectedFileCitacion &&
          !editingNotificacion?.documento_citacion_id && (
            <label className="label">
              <span className="text-xs text-tono-warning">
                ⚠️ No hay documento de citación cargado. Debe subir uno para
                habilitar la sección de notificación.
              </span>
            </label>
          )}
      </div>
    </>
  );
}
