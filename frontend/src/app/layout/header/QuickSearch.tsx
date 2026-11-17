import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import ModuleIcon from "./ModuleIcon";
import { filterPermissions, type HeaderPermission } from "./quickSearchFilter";

type Props = {
  permission: HeaderPermission[];
};

/** Buscador de accesos rápidos (permisos con ruta) del Header. Oculto en móvil. */
export default function QuickSearch({ permission }: Props) {
  const [searchValue, setSearchValue] = useState("");
  const [showResults, setShowResults] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const filteredPermissions = useMemo(
    () => filterPermissions(permission, searchValue),
    [permission, searchValue],
  );

  // Cerrar el desplegable al hacer clic fuera.
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowResults(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleChange = (value: string) => {
    setSearchValue(value);
    setShowResults(filterPermissions(permission, value).length > 0);
  };

  const handleNavigate = (path: string) => {
    navigate(path);
    setSearchValue("");
    setShowResults(false);
  };

  return (
    <div className="hidden md:block relative" ref={searchRef}>
      <div className="relative">
        <input
          type="text"
          placeholder="Buscar acceso rápido..."
          value={searchValue}
          onChange={(e) => handleChange(e.target.value)}
          onFocus={() => searchValue && setShowResults(true)}
          className="input input-sm w-48 lg:w-64 pr-10"
        />
        <button className="absolute right-2 top-1/2 -translate-y-1/2 btn btn-ghost btn-xs btn-circle">
          <svg
            className="w-4 h-4 text-base-content/60"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </button>
      </div>

      {/* Dropdown de resultados */}
      {showResults && filteredPermissions.length > 0 && (
        <div className="absolute top-full mt-2 w-80 bg-base-100 rounded-lg shadow-xl border border-base-300 max-h-96 overflow-y-auto z-50">
          <div className="p-2">
            <div className="text-xs font-semibold text-base-content/60 px-3 py-2">
              Accesos rápidos ({filteredPermissions.length})
            </div>
            {filteredPermissions.map((perm, idx) => (
              <button
                key={idx}
                onClick={() => handleNavigate(perm.path)}
                className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-base-200 rounded-lg transition-colors text-left group"
              >
                <div className="flex-shrink-0 w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-primary-content transition-colors">
                  <ModuleIcon module={perm.module} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm text-base-content group-hover:text-primary transition-colors">
                    {perm.action}
                  </div>
                  <div className="text-xs text-base-content/60 flex items-center gap-1">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-base-200 rounded-full">
                      {perm.module}
                    </span>
                  </div>
                </div>
                <svg
                  className="w-4 h-4 text-base-content/30 group-hover:text-primary group-hover:translate-x-1 transition-all"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Sin resultados */}
      {showResults && filteredPermissions.length === 0 && searchValue && (
        <div className="absolute top-full mt-2 w-80 bg-base-100 rounded-lg shadow-xl border border-base-300 p-4 z-50">
          <div className="text-center text-base-content/60">
            <svg
              className="w-12 h-12 mx-auto mb-2 text-base-content/30"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="text-sm">No se encontraron accesos</p>
            <p className="text-xs mt-1">Intenta con otro término</p>
          </div>
        </div>
      )}
    </div>
  );
}
