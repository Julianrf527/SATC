import { Campo } from "@shared/ui/form/Campo";

type Opcion<T> = { value: T; label: string };

type Props<T extends string | number> = {
  etiqueta: string;
  opciones: Opcion<T>[];
  seleccionados: T[];
  onToggle: (valor: T) => void;
  disabled?: boolean;
  /** Mensaje si el catálogo llega vacío. */
  vacio?: string;
};

/**
 * Lista de checkboxes con borde (mismo estilo que "Recursos afectados" de
 * infraction). Se usa para fuentes y usos del agua (varios por expediente).
 */
export default function SeleccionMultiple<T extends string | number>({
  etiqueta,
  opciones,
  seleccionados,
  onToggle,
  disabled = false,
  vacio = "Sin opciones",
}: Props<T>) {
  return (
    <Campo
      etiqueta={etiqueta}
      extra={seleccionados.length > 0 ? `${seleccionados.length} seleccionado(s)` : undefined}
    >
      <div className="border border-base-300 rounded-lg max-h-44 overflow-y-auto divide-y divide-base-300">
        {opciones.length === 0 ? (
          <p className="text-xs text-base-content/60 text-center py-4">{vacio}</p>
        ) : (
          opciones.map((o) => {
            const activo = seleccionados.includes(o.value);
            return (
              <label
                key={String(o.value)}
                className={`flex items-center gap-3 px-3 py-2 cursor-pointer transition-colors ${
                  activo ? "bg-success/5" : "hover:bg-base-200"
                }`}
              >
                <input
                  type="checkbox"
                  className="checkbox checkbox-success checkbox-sm"
                  checked={activo}
                  onChange={() => onToggle(o.value)}
                  disabled={disabled}
                />
                <span className="text-sm">{o.label}</span>
              </label>
            );
          })
        )}
      </div>
    </Campo>
  );
}
