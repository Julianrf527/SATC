import {
  camposVisibles,
  siNoCampo,
  textoCampo,
  type CamposConcepto as Campos,
  type ConceptoFinalForm,
} from "../../formularios/conceptoFinal";
import { CampoFecha, CampoSiNo, CampoTexto } from "./Campos";

type Props = {
  form: ConceptoFinalForm;
  onChange: (cambio: Partial<ConceptoFinalForm>) => void;
  /** Definición de los campos del tipo de concepto (llega del backend: `campos`). */
  campos: Campos;
  disabled?: boolean;
};

/** Datos del concepto firmado según su tipo (fecha, caudales, cumple...). Sin el PDF. */
export default function CamposConcepto({ form, onChange, campos, disabled }: Props) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {camposVisibles(campos).map(({ campo, tipo, etiqueta, obligatorio }) => {
        const cambiar = (v: string | boolean) => onChange({ [campo]: v } as Partial<ConceptoFinalForm>);
        switch (tipo) {
          case "fecha":
            return (
              <CampoFecha
                key={campo}
                etiqueta={etiqueta}
                valor={textoCampo(form, campo)}
                onChange={cambiar}
                requerido={obligatorio}
                disabled={disabled}
              />
            );
          case "si_no":
            return (
              <CampoSiNo
                key={campo}
                etiqueta={etiqueta}
                valor={siNoCampo(form, campo)}
                onChange={cambiar}
                si="Cumple"
                no="No cumple"
                requerido={obligatorio}
                disabled={disabled}
              />
            );
          case "entero":
          case "decimal":
            return (
              <CampoTexto
                key={campo}
                etiqueta={etiqueta}
                valor={textoCampo(form, campo)}
                onChange={cambiar}
                requerido={obligatorio}
                inputMode={tipo === "entero" ? "numeric" : "decimal"}
                disabled={disabled}
              />
            );
        }
      })}
    </div>
  );
}
