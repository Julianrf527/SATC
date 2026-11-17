import Icono from "./Icono";
import { ICONOS, TONOS, type Tono } from "./iconos";

type Props = {
  /** Si se pasa, muestra "Cancelar". */
  onCancelar?: () => void;
  textoGuardar: string;
  tono: Tono;
  guardando: boolean;
};

/** Pie de formulario de etapa: [Cancelar] [✓ Guardar] con spinner. */
export default function AccionesFormulario({ onCancelar, textoGuardar, tono, guardando }: Props) {
  return (
    <div className="flex gap-3 justify-end pt-4 border-t border-base-300">
      {onCancelar && (
        <button type="button" onClick={onCancelar} className="btn btn-outline" disabled={guardando}>
          Cancelar
        </button>
      )}
      <button
        type="submit"
        className={`btn ${TONOS[tono].boton} text-white gap-2`}
        disabled={guardando}
      >
        {guardando ? (
          <>
            <span className="loading loading-spinner loading-sm"></span>
            Guardando...
          </>
        ) : (
          <>
            <Icono d={ICONOS.guardar} />
            {textoGuardar}
          </>
        )}
      </button>
    </div>
  );
}
