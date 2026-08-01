import { useState, useEffect } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";

type Rol = {
  id: number;
  nombre: string;
};

type Props = {
  rolRef: React.RefObject<HTMLSelectElement | null>;
};

function capitalize(word: string) {
  return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
}

export default function RolList({ rolRef }: Props) {
  const [rolList, setRolList] = useState<Rol[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadRol() {
      setLoading(true);
      setError("");
      try {
        const res = await apiCall(API_CONFIG.ENDPOINTS.ROL_LIST, {
          method: "GET",
        });

        if (res.ok) {
          // El endpoint /role/all ya filtra los roles cuyos permisos son
          // subconjunto de los permisos del usuario autenticado
          setRolList(res.data as Rol[]);
        } else {
          setError(res.detail || "Error al cargar los roles");
        }
      } catch {
        setError("Error de conexión al cargar los roles");
      } finally {
        setLoading(false);
      }
    }

    loadRol();
  }, []);

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
    <div className="form-control">
      <select
        className="select select-bordered w-full focus:border-green-600"
        ref={rolRef}
        defaultValue="0"
      >
        <option value="0" disabled>
          -- Seleccione un rol --
        </option>
        {rolList.length === 0 ? (
          <option disabled>No hay roles disponibles</option>
        ) : (
          rolList.map((rol) => (
            <option key={rol.id} value={rol.id}>
              {capitalize(rol.nombre)}
            </option>
          ))
        )}
      </select>
      {rolList.length > 0 && (
        <label className="label">
          <span className="label-text-alt text-base-content/50">
            {rolList.length} rol{rolList.length !== 1 ? "es" : ""} disponible{rolList.length !== 1 ? "s" : ""}
          </span>
        </label>
      )}
    </div>
  );
}
