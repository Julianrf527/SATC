import { Campo } from "@shared/ui/form/Campo";

type Props = {
  radicados: string[];
  onChange: (radicados: string[]) => void;
  disabled: boolean;
};

/** Lista editable de radicados asociados (siempre deja al menos una fila). */
export default function RadicadosAsociadosField({ radicados, onChange, disabled }: Props) {
  const cambiar = (index: number, value: string) =>
    onChange(radicados.map((item, i) => (i === index ? value.toUpperCase() : item)));
  const quitar = (index: number) =>
    onChange(radicados.length === 1 ? [""] : radicados.filter((_, i) => i !== index));

  return (
    <Campo etiqueta="Radicados Asociados">
      <div className="space-y-2">
        {radicados.map((radicado, index) => (
          <div key={index} className="flex gap-2">
            <input
              type="text"
              value={radicado}
              onChange={(e) => cambiar(index, e.target.value)}
              placeholder="Ej: 2015IE5678"
              className="input w-full"
              disabled={disabled}
              maxLength={15}
              pattern="^$|^\d{4}(IE|EE|ER)\d{4,5}$"
              title="Debe tener el formato: 4 números + IE o EE o ER + 4 o 5 números (ej: 2015IE5678)"
            />
            <button
              type="button"
              className="btn btn-outline btn-error"
              onClick={() => quitar(index)}
              disabled={disabled}
              title="Eliminar radicado"
            >
              <i className="bx bx-trash"></i>
            </button>
          </div>
        ))}
      </div>
      <div className="mt-2">
        <button
          type="button"
          className="btn btn-outline btn-sm"
          onClick={() => onChange([...radicados, ""])}
          disabled={disabled}
        >
          + Agregar radicado
        </button>
      </div>
    </Campo>
  );
}
