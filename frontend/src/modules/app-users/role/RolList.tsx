import { ApiError } from "@shared/lib/api";
import { useRolesQuery } from "../api/roles";
import CustomSelect from "@shared/ui/form/CustomSelect";

type Props = {
  value: number;
  onChange: (value: number) => void;
};

function capitalize(word: string) {
  return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
}

export default function RolList({ value, onChange }: Props) {
  // Capa de datos: hook de react-query del módulo (ver modules/app-users/api/roles.ts).
  const { data: rolList = [], isPending: loading, error: queryError } = useRolesQuery();
  const error = !queryError
    ? ""
    : queryError instanceof ApiError
      ? queryError.message || "Error al cargar los roles"
      : "Error de conexión al cargar los roles";

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-base-content/60 text-sm py-2">
        <span className="loading loading-spinner loading-sm" />
        Cargando roles disponibles...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 bg-error/10 border border-error/20 rounded-lg p-3 text-sm text-error">
        <svg
          className="w-4 h-4 flex-shrink-0"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        {error}
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      <CustomSelect
        className="focus:border-success"
        value={value}
        onChange={onChange}
        placeholder="-- Seleccione un rol --"
        options={rolList.map((rol) => ({ value: rol.id, label: capitalize(rol.nombre) }))}
      />
      {rolList.length > 0 && (
        <label className="label">
          <span className="text-xs text-base-content/60">
            {rolList.length} rol{rolList.length !== 1 ? "es" : ""} disponible{rolList.length !== 1 ? "s" : ""}
          </span>
        </label>
      )}
    </div>
  );
}
