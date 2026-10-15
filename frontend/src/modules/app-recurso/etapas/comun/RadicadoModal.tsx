import { useState } from "react";
import { FileInput } from "lucide-react";
import type { SetToast } from "../../types";
import { MAX_RADICADO, RADICADO_VACIO, validarRadicado, type RadicadoForm } from "../formularios/radicado";
import type { PeticionEtapa } from "../../api/etapas";
import { CampoFecha, CampoPdf, CampoTexto } from "./campos/Campos";
import ModalFormulario from "./ModalFormulario";
import { useEscritura } from "./useEscritura";

type Props = {
  expedienteId: number;
  titulo: string;
  /** Nombre del documento radicado (p. ej. "Planos", "Escrito del recurso"). */
  documento: string;
  /** Arma la petición con el formulario y el `file_id` subido. */
  peticion: (form: RadicadoForm, fileId: number) => PeticionEtapa;
  setToast: SetToast;
  onClose: () => void;
};

/** Registra un documento radicado por el usuario: radicado, fecha y PDF. */
export default function RadicadoModal({ expedienteId, titulo, documento, peticion, setToast, onClose }: Props) {
  const [form, setForm] = useState<RadicadoForm>(RADICADO_VACIO);
  const [error, setError] = useState<string | null>(null);
  const { ejecutar, ocupado } = useEscritura(expedienteId, setToast);
  const cambiar = (c: Partial<RadicadoForm>) => setForm((f) => ({ ...f, ...c }));

  const guardar = () => {
    const invalido = validarRadicado(form);
    if (invalido) return setError(invalido);
    setError(null);
    ejecutar(
      { archivos: { radicado: form.archivo }, peticion: (ids) => peticion(form, ids.radicado) },
      { exito: `${documento} registrado`, error: `Error al registrar: ${documento.toLowerCase()}`, onSuccess: onClose, onError: setError },
    );
  };

  return (
    <ModalFormulario
      titulo={titulo}
      icono={<FileInput size={20} />}
      ocupado={ocupado}
      error={error}
      textoGuardar="Registrar"
      onGuardar={guardar}
      onClose={onClose}
    >
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <CampoTexto
          etiqueta="Radicado"
          valor={form.radicado}
          onChange={(radicado) => cambiar({ radicado })}
          maxLength={MAX_RADICADO}
          requerido
        />
        <CampoFecha etiqueta="Fecha de radicado" valor={form.fecha_radicado} onChange={(fecha_radicado) => cambiar({ fecha_radicado })} requerido />
      </div>
      <CampoPdf etiqueta={`${documento} (PDF)`} archivo={form.archivo} onChange={(archivo) => cambiar({ archivo })} requerido />
    </ModalFormulario>
  );
}
