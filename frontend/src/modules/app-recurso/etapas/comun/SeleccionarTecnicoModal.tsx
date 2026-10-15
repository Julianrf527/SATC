import { useState } from "react";
import { UserCheck } from "lucide-react";
import type { SetToast } from "../../types";
import CampoTecnico from "./campos/CampoTecnico";
import ModalFormulario from "./ModalFormulario";
import { useEscritura } from "./useEscritura";

type Props = {
  expedienteId: number;
  url: string;
  titulo: string;
  setToast: SetToast;
  onClose: () => void;
};

/** El abogado selecciona el técnico del concepto (plan §4-B). Nace el proceso del concepto. */
export default function SeleccionarTecnicoModal({ expedienteId, url, titulo, setToast, onClose }: Props) {
  const [tecnico, setTecnico] = useState<number | "">("");
  const [error, setError] = useState<string | null>(null);
  const { ejecutar, ocupado } = useEscritura(expedienteId, setToast);

  const guardar = () => {
    if (!tecnico) return setError("Seleccione el técnico");
    setError(null);
    ejecutar(
      { peticion: () => ({ url, method: "POST", body: { tecnico_id: tecnico } }) },
      { exito: "Técnico seleccionado", error: "Error al seleccionar el técnico", onSuccess: onClose, onError: setError },
    );
  };

  return (
    <ModalFormulario
      titulo="Seleccionar técnico"
      subtitulo={titulo}
      icono={<UserCheck size={20} />}
      ocupado={ocupado}
      error={error}
      textoGuardar="Seleccionar"
      onGuardar={guardar}
      onClose={onClose}
      size="md"
    >
      <p className="text-sm text-base-content/70">
        El técnico seleccionado es el único que puede proyectar y cargar este concepto. Recibirá el aviso en Mis informes.
      </p>
      <CampoTecnico valor={tecnico} onChange={setTecnico} requerido />
    </ModalFormulario>
  );
}
