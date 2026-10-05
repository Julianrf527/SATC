import { useRef, useState, type FormEvent } from "react";
import { Lock, Send } from "lucide-react";
import type { AccionDisponible, DatosRevision } from "./types";
import {
  acceptDe,
  BORDE_TONO,
  BOTON_TONO,
  extensionPermitida,
  iconoAccion,
  listaExtensiones,
} from "./visual";

type Props = {
  /** `acciones_disponibles` del detalle: lo único que decide qué se ofrece. */
  acciones: AccionDisponible[];
  onSubmit: (datos: DatosRevision) => void;
  onCancel: () => void;
  isPending?: boolean;
  /** Error del servidor (mutación). */
  error?: string | null;
};

const primeraEjecutable = (acciones: AccionDisponible[]) =>
  acciones.find((a) => !a.bloqueada)?.codigo ?? "";

/**
 * Formulario de revisión. Dibuja exactamente las acciones que manda el
 * backend: su etiqueta y tono, deshabilitadas con su motivo si `bloqueada`,
 * comentario obligatorio si `requiere_comentario` y selector de adjunto solo
 * si `adjunto.permitido` (con sus extensiones).
 */
export function FormRevision({ acciones, onSubmit, onCancel, isPending = false, error }: Props) {
  const [codigo, setCodigo] = useState(() => primeraEjecutable(acciones));
  const [comentario, setComentario] = useState("");
  const [adjunto, setAdjunto] = useState<File | null>(null);
  const [errorLocal, setErrorLocal] = useState("");
  const adjuntoRef = useRef<HTMLInputElement>(null);

  const accion = acciones.find((a) => a.codigo === codigo) ?? null;
  const reglaAdjunto = accion?.adjunto.permitido ? accion.adjunto : null;

  const elegir = (a: AccionDisponible) => {
    if (a.bloqueada) return;
    setCodigo(a.codigo);
    setErrorLocal("");
    if (!a.adjunto.permitido) {
      setAdjunto(null);
      if (adjuntoRef.current) adjuntoRef.current.value = "";
    }
  };

  const enviar = (e: FormEvent) => {
    e.preventDefault();
    if (!accion || accion.bloqueada) {
      setErrorLocal("Selecciona una acción");
      return;
    }
    if (accion.requiere_comentario && !comentario.trim()) {
      setErrorLocal("Esta acción requiere un comentario");
      return;
    }
    setErrorLocal("");
    onSubmit({
      accion: accion.codigo,
      comentario: comentario.trim(),
      adjunto: reglaAdjunto ? adjunto : null,
    });
  };

  const tono = accion?.tono ?? "neutral";
  const IconoEnviar = iconoAccion(accion?.icono) ?? Send;

  return (
    <form onSubmit={enviar} className="space-y-4">
      <fieldset disabled={isPending} className="space-y-4">
        <div>
          <p className="block text-sm font-medium text-base-content/70 mb-2">
            Decisión <span className="text-error">*</span>
          </p>
          <div className="grid gap-2 sm:grid-cols-2" role="radiogroup" aria-label="Decisión">
            {acciones.map((a) => {
              const seleccionada = a.codigo === codigo;
              const Icono = iconoAccion(a.icono);
              return (
                <button
                  key={a.codigo}
                  type="button"
                  role="radio"
                  aria-checked={seleccionada}
                  onClick={() => elegir(a)}
                  disabled={!!a.bloqueada}
                  title={a.bloqueada ?? undefined}
                  className={`p-3 rounded-lg border-2 text-left transition-all disabled:opacity-50 disabled:cursor-not-allowed ${
                    seleccionada ? BORDE_TONO[a.tono] : "border-base-300 hover:border-base-content/30"
                  }`}
                >
                  <span className="font-semibold flex items-center gap-2">
                    {a.bloqueada ? <Lock size={18} /> : Icono && <Icono size={18} />}
                    {a.etiqueta}
                  </span>
                  {a.bloqueada && (
                    <span className="block text-xs text-base-content/60 mt-1">{a.bloqueada}</span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <label htmlFor="proceso-comentario" className="block text-sm font-medium text-base-content/70 mb-1">
            Comentarios
            {accion?.requiere_comentario ? (
              <span className="text-error"> *</span>
            ) : (
              <span className="text-base-content/60 text-xs ml-2">(Opcional)</span>
            )}
          </label>
          <textarea
            id="proceso-comentario"
            className="textarea w-full h-28"
            value={comentario}
            onChange={(e) => setComentario(e.target.value)}
            placeholder={accion?.requiere_comentario ? "Especifique el motivo..." : "Comentarios adicionales..."}
          />
        </div>

        {reglaAdjunto && (
          <div>
            <label htmlFor="proceso-adjunto" className="block text-sm font-medium text-base-content/70 mb-1">
              Documento con observaciones
              <span className="text-base-content/60 text-xs ml-2">
                (Opcional · {listaExtensiones(reglaAdjunto.extensiones)})
              </span>
            </label>
            <input
              id="proceso-adjunto"
              ref={adjuntoRef}
              type="file"
              accept={acceptDe(reglaAdjunto.extensiones)}
              className="file-input file-input-sm w-full"
              onChange={(e) => {
                const file = e.target.files?.[0] ?? null;
                if (file && !extensionPermitida(file.name, reglaAdjunto.extensiones)) {
                  setErrorLocal(`El adjunto debe ser ${listaExtensiones(reglaAdjunto.extensiones)}`);
                  e.target.value = "";
                  setAdjunto(null);
                  return;
                }
                setErrorLocal("");
                setAdjunto(file);
              }}
            />
          </div>
        )}
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
        <button
          type="submit"
          className={`btn ${BOTON_TONO[tono]} text-white gap-2`}
          disabled={isPending || !accion || !!accion.bloqueada}
        >
          {isPending ? <span className="loading loading-spinner loading-sm" /> : <IconoEnviar size={16} />}
          {accion ? accion.etiqueta : "Enviar"}
        </button>
      </div>
    </form>
  );
}

export default FormRevision;
