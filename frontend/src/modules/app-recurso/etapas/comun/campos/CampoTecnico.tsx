import { useTecnicosQuery } from "../../../api/etapas";
import { CampoOpciones } from "./Campos";

type Props = {
  etiqueta?: string;
  valor: number | "";
  onChange: (v: number | "") => void;
  requerido?: boolean;
  disabled?: boolean;
};

/** Técnico encargado: usuarios con `recurso_tecnico` (GET /etapas/tecnicos). */
export default function CampoTecnico({ etiqueta = "Técnico encargado", valor, onChange, requerido, disabled }: Props) {
  const { data = [], isPending, isError } = useTecnicosQuery();
  const opciones = data.map((t) => ({ value: t.id, label: t.nombre ?? t.correo ?? `Usuario #${t.id}` }));
  return (
    <div>
      <CampoOpciones<number>
        etiqueta={etiqueta}
        valor={valor}
        opciones={opciones}
        onChange={onChange}
        requerido={requerido}
        placeholder={isPending ? "Cargando técnicos..." : "Seleccione el técnico..."}
        disabled={disabled || isPending}
      />
      {isError && <p className="text-xs text-error mt-1">No se pudo cargar la lista de técnicos</p>}
      {!isPending && !isError && opciones.length === 0 && (
        <p className="text-xs text-tono-warning mt-1">No hay usuarios con el permiso de técnico</p>
      )}
    </div>
  );
}
