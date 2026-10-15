import { useState } from "react";
import { UserPlus } from "lucide-react";
import { Modal } from "@shared/ui";
import type { SetToast } from "../../types";
import { useEscritura } from "./useEscritura";

type Props = {
  expedienteId: number;
  url: string;
  /** Qué se asigna (p. ej. "el auto que admite"). */
  que: string;
  setToast: SetToast;
  /** Botón grande (estado vacío de la etapa) o pequeño (sub-proceso). */
  grande?: boolean;
};

/**
 * "Asignarme para diligenciar" (plan §4-A): crea la fila y el proceso de
 * revisión con el usuario como encargado. No hay reasignación, por eso se confirma.
 */
export default function BotonAsignarme({ expedienteId, url, que, setToast, grande }: Props) {
  const [confirmar, setConfirmar] = useState(false);
  const { ejecutar, ocupado } = useEscritura(expedienteId, setToast);

  const asignar = () =>
    ejecutar(
      { peticion: () => ({ url, method: "POST" }) },
      {
        exito: "Asignado. Ya puede proyectar el documento",
        error: "Error al asignarse",
        onSuccess: () => setConfirmar(false),
        onError: (mensaje) => {
          setToast({ id: Date.now(), message: mensaje, type: "error" });
          setConfirmar(false);
        },
      },
    );

  return (
    <>
      <button
        type="button"
        className={
          grande
            ? "btn btn-success text-white btn-lg gap-2 shadow-md hover:shadow-lg transition-all"
            : "btn btn-success btn-sm text-white gap-1.5"
        }
        onClick={() => setConfirmar(true)}
        disabled={ocupado}
      >
        <UserPlus size={grande ? 20 : 14} />
        Asignarme para diligenciar
      </button>
      <Modal
        isOpen={confirmar}
        onClose={() => setConfirmar(false)}
        size="sm"
        icon={<UserPlus size={20} />}
        title="Asignarme para diligenciar"
        closeOnEsc={!ocupado}
        closeOnBackdrop={!ocupado}
        footer={
          <>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setConfirmar(false)} disabled={ocupado}>
              Cancelar
            </button>
            <button type="button" className="btn btn-success btn-sm text-white" onClick={asignar} disabled={ocupado}>
              {ocupado && <span className="loading loading-spinner loading-xs" />}
              Asignarme
            </button>
          </>
        }
      >
        <p className="text-sm">
          ¿Asignarse {que}? Desde ese momento solo usted podrá gestionarlo y no se puede reasignar.
        </p>
      </Modal>
    </>
  );
}
