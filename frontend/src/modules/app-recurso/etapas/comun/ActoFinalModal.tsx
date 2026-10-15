import { useState } from "react";
import { FileSignature } from "lucide-react";
import type { SetToast } from "../../types";
import {
  ACTO_FINAL_VACIO,
  bodyActoFinal,
  OPCIONES_DECISION,
  OPCIONES_RESULTADO,
  validarActoFinal,
  type ActoFinalForm,
  type VarianteActoFinal,
} from "../formularios/actoFinal";
import { OPCIONES_CLASE_ACTO } from "../formularios/comunes";
import { CampoFecha, CampoOpciones, CampoPdf, CampoSiNo, CampoTexto } from "./campos/Campos";
import CampoTecnico from "./campos/CampoTecnico";
import ModalFormulario from "./ModalFormulario";
import { useEscritura } from "./useEscritura";

type Props = {
  expedienteId: number;
  /** URL de `.../version-final` del nodo. */
  url: string;
  titulo: string;
  variante: VarianteActoFinal;
  setToast: SetToast;
  onClose: () => void;
};

const AYUDA: Record<VarianteActoFinal, string | null> = {
  simple: null,
  admite:
    "Diligencie el técnico y la fecha de visita escritos en el auto: con ellos nace la etapa 2 (concepto técnico) y el técnico recibe el aviso.",
  decision: "La decisión se toma una sola vez por expediente.",
  recurso: null,
};

/**
 * "Cargar versión final" de un acto (C.1): el encargado sube el PDF firmado
 * y diligencia los datos escritos en él. El backend crea el acto y deja el
 * documento "Aprobado".
 */
export default function ActoFinalModal({ expedienteId, url, titulo, variante, setToast, onClose }: Props) {
  const [form, setForm] = useState<ActoFinalForm>(ACTO_FINAL_VACIO);
  const [error, setError] = useState<string | null>(null);
  const { ejecutar, ocupado } = useEscritura(expedienteId, setToast);
  const cambiar = (c: Partial<ActoFinalForm>) => setForm((f) => ({ ...f, ...c }));

  const guardar = () => {
    const invalido = validarActoFinal(form, variante);
    if (invalido) return setError(invalido);
    setError(null);
    ejecutar(
      {
        archivos: { acto: form.archivo },
        peticion: (ids) => ({ url, method: "POST", body: bodyActoFinal(form, variante, ids.acto) }),
      },
      { exito: "Versión final cargada", error: "Error al cargar la versión final", onSuccess: onClose, onError: setError },
    );
  };

  return (
    <ModalFormulario
      titulo="Cargar versión final"
      subtitulo={titulo}
      icono={<FileSignature size={20} />}
      ocupado={ocupado}
      error={error}
      textoGuardar="Cargar versión final"
      onGuardar={guardar}
      onClose={onClose}
    >
      {AYUDA[variante] && <p className="text-sm text-base-content/70">{AYUDA[variante]}</p>}
      <CampoPdf etiqueta="Acto firmado y numerado (PDF)" archivo={form.archivo} onChange={(archivo) => cambiar({ archivo })} requerido />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <CampoOpciones
          etiqueta="Tipo de acto"
          valor={form.clase_acto}
          opciones={OPCIONES_CLASE_ACTO}
          onChange={(clase_acto) => cambiar({ clase_acto })}
          requerido
        />
        <CampoTexto
          etiqueta="Numerado"
          valor={form.numerado}
          onChange={(v) => cambiar({ numerado: v.replace(/\D/g, "").slice(0, 4) })}
          placeholder="0012"
          inputMode="numeric"
          requerido
        />
      </div>
      <CampoFecha
        etiqueta="Fecha de numerado"
        valor={form.fecha_numerado}
        onChange={(v) => cambiar({ fecha_numerado: v })}
        requerido
      />

      {variante === "admite" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <CampoTecnico valor={form.tecnico_id} onChange={(v) => cambiar({ tecnico_id: v })} requerido />
          <CampoFecha
            etiqueta="Fecha de visita técnica"
            valor={form.fecha_visita_tecnica}
            onChange={(v) => cambiar({ fecha_visita_tecnica: v })}
            permitirFutura
            requerido
          />
        </div>
      )}

      {variante === "decision" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <CampoOpciones
            etiqueta="Decisión"
            valor={form.decision}
            opciones={OPCIONES_DECISION}
            onChange={(v) => cambiar({ decision: v, requiere_memorias: v === "OTORGADA" ? form.requiere_memorias : null })}
            requerido
          />
          {form.decision === "OTORGADA" && (
            <CampoSiNo
              etiqueta="¿Exige memorias de cálculo (planos)?"
              valor={form.requiere_memorias}
              onChange={(v) => cambiar({ requiere_memorias: v })}
              no="No (solo medidor o llave)"
              requerido
            />
          )}
        </div>
      )}

      {variante === "recurso" && (
        <CampoOpciones
          etiqueta="Resultado del recurso"
          valor={form.resultado}
          opciones={OPCIONES_RESULTADO}
          onChange={(v) => cambiar({ resultado: v })}
          requerido
        />
      )}
    </ModalFormulario>
  );
}
