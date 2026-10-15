import { useState } from "react";
import { FileSignature } from "lucide-react";
import type { DatosConcepto, SetToast, TipoConcepto } from "../../types";
import {
  bodyConceptoFinal,
  camposConcepto,
  conceptoFinalInicial,
  validarConceptoFinal,
  type ConceptoFinalForm,
} from "../formularios/conceptoFinal";
import { CampoPdf } from "./campos/Campos";
import CamposConcepto from "./campos/CamposConcepto";
import ModalFormulario from "./ModalFormulario";
import { useEscritura } from "./useEscritura";

type Props = {
  expedienteId: number;
  url: string;
  tipo: TipoConcepto;
  titulo: string;
  datos: Partial<DatosConcepto>;
  setToast: SetToast;
  onClose: () => void;
};

/** "Cargar versión final" del concepto técnico (técnico seleccionado, C.4). */
export default function ConceptoFinalModal({ expedienteId, url, tipo, titulo, datos, setToast, onClose }: Props) {
  const campos = camposConcepto(tipo);
  const [form, setForm] = useState<ConceptoFinalForm>(() => conceptoFinalInicial(datos));
  const [error, setError] = useState<string | null>(null);
  const { ejecutar, ocupado } = useEscritura(expedienteId, setToast);

  const guardar = () => {
    const invalido = validarConceptoFinal(form, campos);
    if (invalido) return setError(invalido);
    setError(null);
    ejecutar(
      {
        archivos: { concepto: form.archivo },
        peticion: (ids) => ({ url, method: "POST", body: bodyConceptoFinal(form, campos, ids.concepto) }),
      },
      { exito: "Concepto técnico cargado", error: "Error al cargar el concepto", onSuccess: onClose, onError: setError },
    );
  };

  return (
    <ModalFormulario
      titulo="Cargar versión final del concepto"
      subtitulo={titulo}
      icono={<FileSignature size={20} />}
      ocupado={ocupado}
      error={error}
      textoGuardar="Cargar concepto"
      onGuardar={guardar}
      onClose={onClose}
    >
      <CampoPdf etiqueta="Concepto firmado (PDF)" archivo={form.archivo} onChange={(archivo) => setForm((f) => ({ ...f, archivo }))} requerido />
      <CamposConcepto form={form} onChange={(c) => setForm((f) => ({ ...f, ...c }))} campos={campos} />
    </ModalFormulario>
  );
}
