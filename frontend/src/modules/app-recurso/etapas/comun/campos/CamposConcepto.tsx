import {
  camposVisibles,
  ETIQUETAS_CAMPO_CONCEPTO,
  type CamposConcepto as Campos,
  type ConceptoFinalForm,
} from "../../formularios/conceptoFinal";
import { CampoFecha, CampoSiNo, CampoTexto } from "./Campos";

type Props = {
  form: ConceptoFinalForm;
  onChange: (cambio: Partial<ConceptoFinalForm>) => void;
  /** Obligatorios / opcionales del tipo de concepto (backend o `camposConcepto`). */
  campos: Campos;
  disabled?: boolean;
};

/** Datos del concepto firmado según su tipo (fecha, caudales, cumple...). Sin el PDF. */
export default function CamposConcepto({ form, onChange, campos, disabled }: Props) {
  const requerido = (c: string) => campos.obligatorios.includes(c);
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {camposVisibles(campos).map((campo) => {
        const etiqueta = ETIQUETAS_CAMPO_CONCEPTO[campo];
        switch (campo) {
          case "fecha_aceptacion":
          case "fecha_visita_tecnica":
            return (
              <CampoFecha
                key={campo}
                etiqueta={etiqueta}
                valor={form[campo]}
                onChange={(v) => onChange({ [campo]: v })}
                requerido={requerido(campo)}
                disabled={disabled}
              />
            );
          case "cumple":
            return (
              <CampoSiNo
                key={campo}
                etiqueta={etiqueta}
                valor={form.cumple}
                onChange={(v) => onChange({ cumple: v })}
                si="Cumple"
                no="No cumple"
                requerido={requerido(campo)}
                disabled={disabled}
              />
            );
          default:
            return (
              <CampoTexto
                key={campo}
                etiqueta={etiqueta}
                valor={form[campo]}
                onChange={(v) => onChange({ [campo]: v })}
                requerido={requerido(campo)}
                inputMode={campo === "num_usuarios" ? "numeric" : "decimal"}
                disabled={disabled}
              />
            );
        }
      })}
    </div>
  );
}
