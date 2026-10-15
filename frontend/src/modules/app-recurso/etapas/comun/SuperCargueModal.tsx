import { useState } from "react";
import { DatabaseZap } from "lucide-react";
import type { SetToast } from "../../types";
import { urlSuperCargue, type RefNodo } from "../nodos";
import {
  archivosSuper,
  bodySuper,
  seccionesSuper,
  SUPER_VACIO,
  superVacio,
  validarSuper,
  type SuperCargueForm,
} from "../formularios/superCargue";
import ModalFormulario from "./ModalFormulario";
import SuperCargueCampos from "./SuperCargueCampos";
import { useEscritura } from "./useEscritura";

type Props = {
  expedienteId: number;
  refNodo: RefNodo;
  titulo: string;
  /** Datos del nodo: la fila existe, su `version` y si ya tiene acto. */
  existe: boolean;
  version: number | null;
  tieneActo: boolean;
  actuales?: Partial<Record<"radicado" | "oficio" | "fijacion" | "constancia" | "concepto" | "respuesta", number | null>>;
  setToast: SetToast;
  onClose: () => void;
};

/**
 * Cargue directo de super gestión (plan §2.1, C.9): documento final + datos
 * de la etapa sin asignación ni revisión, como el cargue manual de infraction.
 * Si la fila no existe se crea; si existe solo se actualiza lo diligenciado.
 */
export default function SuperCargueModal({
  expedienteId,
  refNodo,
  titulo,
  existe,
  version,
  tieneActo,
  actuales = {},
  setToast,
  onClose,
}: Props) {
  const s = seccionesSuper(refNodo, tieneActo);
  const [form, setForm] = useState<SuperCargueForm>(SUPER_VACIO);
  const [error, setError] = useState<string | null>(null);
  const { ejecutar, ocupado } = useEscritura(expedienteId, setToast);

  const guardar = () => {
    const invalido = validarSuper(s, form, existe);
    if (invalido) return setError(invalido);
    const archivos = archivosSuper(s, form);
    // Comprobación previa (sin subir nada): ¿hay algo que cargar?
    const marcadores = Object.fromEntries(Object.entries(archivos).filter(([, f]) => f).map(([k]) => [k, 1]));
    if (superVacio(bodySuper(s, form, marcadores, version))) return setError("Diligencie al menos un dato para cargar");
    setError(null);
    ejecutar(
      {
        archivos,
        peticion: (ids) => ({ url: urlSuperCargue(expedienteId, refNodo), method: "POST", body: bodySuper(s, form, ids, version) }),
      },
      { exito: "Cargue directo realizado", error: "Error en el cargue directo", onSuccess: onClose, onError: setError },
    );
  };

  return (
    <ModalFormulario
      titulo="Cargue directo (super gestión)"
      subtitulo={titulo}
      icono={<DatabaseZap size={20} />}
      ocupado={ocupado}
      error={error}
      textoGuardar="Cargar"
      onGuardar={guardar}
      onClose={onClose}
      size="2xl"
    >
      <p className="text-sm text-base-content/70">
        Cargue de expedientes históricos: no pasa por asignación, revisión ni validaciones del flujo.
        {existe ? " Solo se actualizan los datos que diligencie." : " Se crea la etapa con los datos diligenciados."}
      </p>
      {tieneActo && (s.actoObligatorio || refNodo.clase !== "concepto") && (
        <p className="text-xs text-base-content/60">El acto ya existe: para corregirlo use Editar en el acto administrativo.</p>
      )}
      <SuperCargueCampos s={s} form={form} cambiar={(c) => setForm((f) => ({ ...f, ...c }))} existe={existe} actuales={actuales} />
    </ModalFormulario>
  );
}
