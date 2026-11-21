import { useState } from "react";
import { FileSignature } from "lucide-react";
import { toastService } from "@shared/lib/toastService";
import { useVersionFinalActoMutation } from "../../api/actos";
import { detalleError } from "../../api/errors";
import ModalFormulario from "../ModalFormulario";
import CamposActo from "./CamposActo";
import { DATOS_ACTO_VACIO, validarDatosActo, type DatosActo } from "./datosActo";

type Props = {
  procesoId: number;
  titulo: string;
  onClose: () => void;
};

/**
 * "Cargar versión final" (como `ActoFinalModal` de recurso): con el acto
 * aprobado para firma, el encargado sube el PDF firmado y numerado con tipo,
 * numerado y fecha. El backend aprueba el proceso y crea el acto de la etapa
 * (POST /revision-actos/{id}/version-final).
 */
export default function ActoFinalModal({ procesoId, titulo, onClose }: Props) {
  const [datos, setDatos] = useState<DatosActo>(DATOS_ACTO_VACIO);
  const [error, setError] = useState<string | null>(null);
  const cargar = useVersionFinalActoMutation(procesoId);

  const guardar = () => {
    const invalido = validarDatosActo(datos);
    if (invalido) return setError(invalido);
    setError(null);
    cargar.mutate(
      { archivo: datos.archivo!, tipoActo: datos.tipoActo, numerado: datos.numerado, fechaNumerado: datos.fecha },
      {
        onSuccess: (res) => {
          toastService.showToast({ id: Date.now(), message: res?.message || "Versión final cargada", type: "success" });
          onClose();
        },
        onError: (err) => setError(detalleError(err) ?? "Error al cargar la versión final"),
      },
    );
  };

  return (
    <ModalFormulario
      titulo="Cargar versión final"
      subtitulo={titulo}
      icono={<FileSignature size={20} />}
      ocupado={cargar.isPending}
      error={error}
      textoGuardar="Cargar versión final"
      onGuardar={guardar}
      onClose={onClose}
    >
      <CamposActo
        datos={datos}
        cambiar={(c) => {
          setDatos((d) => ({ ...d, ...c }));
          setError(null);
        }}
      />
    </ModalFormulario>
  );
}
