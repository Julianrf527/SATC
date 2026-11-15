import { useState } from "react";
import { FlaskConical } from "lucide-react";
import type { SetToast } from "../../types";
import { CampoSiNo } from "../comun/campos/Campos";
import ModalFormulario from "../comun/ModalFormulario";
import { useEscritura } from "../comun/useEscritura";
import { bodyRequierePruebas, validarRequierePruebas } from "../formularios/requierePruebas";
import { urlRequierePruebas } from "../nodos";

type Props = {
  expedienteId: number;
  /** Versión del recurso (control optimista). */
  version: number;
  actual: boolean;
  /** Sí → No con la práctica iniciada: qué se elimina (del backend). */
  avisoEliminar?: string;
  setToast: SetToast;
  onClose: () => void;
};

/**
 * Cambia «¿Requiere práctica de pruebas?» del recurso (cualquier abogado).
 * Pasar a «No» con la práctica iniciada la elimina: se muestra el aviso del
 * backend y se exige confirmarlo. Con el concepto de pruebas creado (o el
 * acto que resuelve cargado, para pasar a «Sí») el backend no ofrece la acción.
 */
export default function RequierePruebasModal({ expedienteId, version, actual, avisoEliminar, setToast, onClose }: Props) {
  const [requiere, setRequiere] = useState(actual);
  const [confirmado, setConfirmado] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { ejecutar, ocupado } = useEscritura(expedienteId, setToast);
  const elimina = actual && !requiere && !!avisoEliminar;

  const guardar = () => {
    const invalido = validarRequierePruebas(actual, requiere, elimina, confirmado);
    if (invalido) return setError(invalido);
    setError(null);
    ejecutar(
      {
        peticion: () => ({
          url: urlRequierePruebas(expedienteId),
          method: "PUT",
          body: bodyRequierePruebas(version, requiere, elimina && confirmado),
        }),
      },
      { exito: "Práctica de pruebas actualizada", error: "Error al cambiar la práctica de pruebas", onSuccess: onClose, onError: setError },
    );
  };

  return (
    <ModalFormulario
      titulo="Práctica de pruebas"
      icono={<FlaskConical size={20} />}
      ocupado={ocupado}
      error={error}
      textoGuardar="Guardar"
      onGuardar={guardar}
      onClose={onClose}
      size="md"
    >
      <CampoSiNo etiqueta="¿Requiere práctica de pruebas?" valor={requiere} onChange={setRequiere} requerido />
      {elimina && (
        <div role="alert" className="alert alert-error flex-col items-start gap-2 text-sm">
          <span className="font-semibold">{avisoEliminar}</span>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              className="checkbox checkbox-sm"
              checked={confirmado}
              onChange={(e) => setConfirmado(e.target.checked)}
            />
            Entiendo y quiero eliminar la práctica de pruebas
          </label>
        </div>
      )}
    </ModalFormulario>
  );
}
