import { useState } from "react";
import { DatabaseZap } from "lucide-react";
import type { ActoAdminFormData, ActoAdminSaveResult } from "@features/acto-administrativo";
import { getErrorMessage } from "@shared/lib/api";
import { uploadFileToDocuments } from "@shared/lib/fileUpload";
import { Seccion } from "../campos/Campos";
import ModalFormulario from "../ModalFormulario";
import CamposActo from "./CamposActo";
import { DATOS_ACTO_VACIO, validarDatosActo, type DatosActo } from "./datosActo";

type Props = {
  /** Nombre del documento ("Acto de cierre"...). */
  titulo: string;
  /** Hay un proceso de revisión en curso: se cerrará. */
  conProceso: boolean;
  /** Guardado de `ActoAdmin` (POST /actos/administrativos: solo super gestión). */
  onSave: (datos: ActoAdminFormData) => Promise<ActoAdminSaveResult>;
  onClose: () => void;
};

/**
 * Cargue directo del acto (como `SuperCargueModal` de recurso): acto firmado
 * + tipo, numerado y fecha, sin pasar por el proceso de revisión. El backend
 * crea el acto en la etapa y cierra el proceso vigente si lo hay.
 */
export default function SuperCargueActoModal({ titulo, conProceso, onSave, onClose }: Props) {
  const [datos, setDatos] = useState<DatosActo>(DATOS_ACTO_VACIO);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const guardar = async () => {
    const invalido = validarDatosActo(datos);
    if (invalido) return setError(invalido);
    setError(null);
    setOcupado(true);
    try {
      const documento = await uploadFileToDocuments(datos.archivo!, datos.archivo!.name);
      const res = await onSave({
        tipo_acto: datos.tipoActo,
        numerado: datos.numerado,
        fecha_numerado: datos.fecha,
        documento_acto_id: documento,
        radicado_expediente: "",
        etapa_id: 0,
      });
      if (res.ok) {
        onClose();
        return;
      }
      setError(res.error ?? "Error en el cargue directo");
    } catch (e) {
      setError(getErrorMessage(e, "Error al subir el archivo"));
    } finally {
      setOcupado(false);
    }
  };

  return (
    <ModalFormulario
      titulo="Cargue directo (super gestión)"
      subtitulo={titulo}
      icono={<DatabaseZap size={20} />}
      ocupado={ocupado}
      error={error}
      textoGuardar="Cargar"
      onGuardar={() => void guardar()}
      onClose={onClose}
    >
      <p className="text-sm text-base-content/70">
        Cargue de expedientes históricos: el acto queda expedido sin pasar por el proceso de revisión.
        {conProceso && " El proceso de revisión en curso se cerrará."}
      </p>
      <Seccion titulo="Acto administrativo firmado">
        <CamposActo
          datos={datos}
          cambiar={(c) => {
            setDatos((d) => ({ ...d, ...c }));
            setError(null);
          }}
        />
      </Seccion>
    </ModalFormulario>
  );
}
