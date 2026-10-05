import { useState, type FormEvent } from "react";
import { Upload } from "lucide-react";
import type { DatosVersion, SubidaVersion } from "./types";
import { acceptDe, extensionPermitida, listaExtensiones } from "./visual";

type Props = {
  /** `subida_version` del detalle: extensiones y si está permitida. */
  regla: SubidaVersion;
  onSubmit: (datos: DatosVersion) => void;
  onCancel: () => void;
  isPending?: boolean;
  error?: string | null;
};

/** Subida de una nueva versión, restringida a lo que diga `subida_version`. */
export function FormSubirVersion({ regla, onSubmit, onCancel, isPending = false, error }: Props) {
  const [archivo, setArchivo] = useState<File | null>(null);
  const [comentario, setComentario] = useState("");
  const [errorLocal, setErrorLocal] = useState("");

  const enviar = (e: FormEvent) => {
    e.preventDefault();
    if (!archivo) {
      setErrorLocal("Debe seleccionar un archivo");
      return;
    }
    setErrorLocal("");
    onSubmit({ archivo, comentario: comentario.trim() });
  };

  if (!regla.permitida) {
    return (
      <div role="status" className="alert py-2 text-sm">
        {regla.motivo ?? "En el estado actual no se puede subir una nueva versión"}
      </div>
    );
  }

  return (
    <form onSubmit={enviar} className="space-y-4">
      <fieldset disabled={isPending} className="space-y-4">
        <div>
          <label htmlFor="proceso-archivo" className="block text-sm font-medium text-base-content/70 mb-1">
            Archivo <span className="text-error">*</span>
            <span className="text-xs text-base-content/60 ml-2">({listaExtensiones(regla.extensiones)})</span>
          </label>
          <input
            id="proceso-archivo"
            type="file"
            accept={acceptDe(regla.extensiones)}
            className="file-input w-full"
            onChange={(e) => {
              const file = e.target.files?.[0] ?? null;
              if (file && !extensionPermitida(file.name, regla.extensiones)) {
                setErrorLocal(`Formato no permitido. Permitidos: ${listaExtensiones(regla.extensiones)}`);
                e.target.value = "";
                setArchivo(null);
                return;
              }
              setErrorLocal("");
              setArchivo(file);
            }}
          />
        </div>
        <div>
          <label htmlFor="proceso-version-comentario" className="block text-sm font-medium text-base-content/70 mb-1">
            Comentario sobre los cambios
            <span className="text-base-content/60 text-xs ml-2">(Opcional)</span>
          </label>
          <textarea
            id="proceso-version-comentario"
            className="textarea w-full h-24"
            value={comentario}
            onChange={(e) => setComentario(e.target.value)}
            placeholder="Describa brevemente los cambios realizados..."
          />
        </div>
      </fieldset>

      {(errorLocal || error) && (
        <div role="alert" className="alert alert-error py-2 text-sm">
          {errorLocal || error}
        </div>
      )}

      <div className="flex justify-end gap-2 pt-2 border-t border-base-300">
        <button type="button" onClick={onCancel} className="btn btn-ghost" disabled={isPending}>
          Cancelar
        </button>
        <button type="submit" className="btn btn-primary gap-2" disabled={isPending || !archivo}>
          {isPending ? <span className="loading loading-spinner loading-sm" /> : <Upload size={16} />}
          Subir versión
        </button>
      </div>
    </form>
  );
}

export default FormSubirVersion;
