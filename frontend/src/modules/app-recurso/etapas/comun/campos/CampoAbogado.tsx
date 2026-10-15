import { useAbogadosQuery } from "../../../api/etapas";
import { CampoOpciones } from "./Campos";

type Props = {
  valor: number | "";
  onChange: (v: number | "") => void;
  /** La fila ya existe: vacío conserva el encargado actual. */
  existe: boolean;
  disabled?: boolean;
};

/**
 * Abogado encargado opcional del cargue directo (usuarios con
 * `recurso_gestionar`, GET /etapas/abogados). Vacío = "Sin encargado".
 */
export default function CampoAbogado({ valor, onChange, existe, disabled }: Props) {
  const { data = [], isPending, isError } = useAbogadosQuery();
  const opciones = data.map((a) => ({ value: a.id, label: a.nombre ?? a.correo ?? `Usuario #${a.id}` }));
  return (
    <div>
      <CampoOpciones<number>
        etiqueta="Abogado encargado"
        valor={valor}
        opciones={opciones}
        onChange={onChange}
        placeholder={isPending ? "Cargando abogados..." : existe ? "Sin cambio (conservar el actual)" : "Sin encargado"}
        disabled={disabled || isPending}
      />
      <p className="text-xs text-base-content/60 mt-1">
        {existe
          ? "Opcional. Si elige otro abogado, el proceso de revisión abierto pasa a su nombre."
          : "Opcional. Sin encargado (expedientes antiguos) nadie se asigna la etapa y solo super gestión la gestiona."}
      </p>
      {isError && <p className="text-xs text-error mt-1">No se pudo cargar la lista de abogados</p>}
    </div>
  );
}
