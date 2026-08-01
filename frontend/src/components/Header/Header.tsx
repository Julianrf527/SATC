import { useEffect, useState, useRef } from "react";
import { apiCall, API_CONFIG } from "../../utils/api";
import { Link, useNavigate } from "react-router-dom";
import ImgProfile from "../Image/ImgProfile";
import Notifications from "./Notifications";

type Props = {
  setTheme: (theme: "emerald" | "dark") => void;
  permission: { name: string; path: string }[];
};

type FormattedPermission = {
  original: string;
  action: string;
  module: string;
  path: string;
};

export default function Header({ setTheme, permission = [] }: Props) {
  const [notification, setNotification] = useState<any[] | null>(null);
  const [isDark, setIsDark] = useState(() => {
    return localStorage.getItem("theme") === "dark";
  });
  const [searchValue, setSearchValue] = useState("");
  const [showResults, setShowResults] = useState(false);
  const [filteredPermissions, setFilteredPermissions] = useState<
    FormattedPermission[]
  >([]);
  const searchRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const formatPermissions = (
    perms: { name: string; path: string }[],
  ): FormattedPermission[] => {
    return perms.map((perm) => {
      const parts = perm.name.split("_");

      const actionMap: { [key: string]: string } = {
        agregar: "Agregar",
        gestionar: "Gestionar",
        roles: "Roles",
        permisos: "Permisos",
        asignar: "Asignar",
        encargados: "Encargados",
      };

      const moduleMap: { [key: string]: string } = {
        usuarios: "Usuarios",
        expediente: "Expediente",
        file: "Archivo",
        user: "Usuario",
      };

      let action = "";
      let module = "";

      if (parts.length >= 2) {
        const modulePart = parts[0];
        const actionPart = parts.slice(1).join(" ");

        module =
          moduleMap[modulePart] ||
          modulePart.charAt(0).toUpperCase() + modulePart.slice(1);
        action =
          actionMap[actionPart] ||
          actionPart
            .split(" ")
            .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
            .join(" ");
      } else {
        action =
          actionMap[parts[0]] ||
          parts[0].charAt(0).toUpperCase() + parts[0].slice(1);
        module = "Sistema";
      }

      return {
        original: perm.name,
        action,
        module,
        path: perm.path,
      };
    });
  };

  useEffect(() => {
    if (searchValue.trim() === "") {
      setFilteredPermissions([]);
      setShowResults(false);
      return;
    }

    const formatted = formatPermissions(permission || []);
    const searchLower = searchValue.toLowerCase();

    const filtered = formatted.filter(
      (perm) =>
        perm.action.toLowerCase().includes(searchLower) ||
        perm.module.toLowerCase().includes(searchLower) ||
        perm.original.toLowerCase().includes(searchLower),
    );

    setFilteredPermissions(filtered);
    setShowResults(filtered.length > 0);
  }, [searchValue, permission]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        searchRef.current &&
        !searchRef.current.contains(event.target as Node)
      ) {
        setShowResults(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    const endpoint = API_CONFIG.ENDPOINTS.NOTIFICATION_STREAM;
    let baseUrl =
      window.ENV?.VITE_API_URL ?? import.meta.env.VITE_API_URL ?? "";
    if (baseUrl.endsWith("/")) baseUrl = baseUrl.slice(0, -1);
    const streamUrl = `${baseUrl}${endpoint}`;

    let eventSource: EventSource | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      eventSource = new window.EventSource(streamUrl, {
        withCredentials: true,
      });

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.notifications) {
            setNotification(data.notifications);
          }
        } catch (e) {
          // Puede ser heartbeat u otro mensaje
        }
      };

      eventSource.onerror = () => {
        if (eventSource) {
          eventSource.close();
          eventSource = null;
        }

        // Reintento simple para mantener el stream activo
        if (!reconnectTimer) {
          reconnectTimer = setTimeout(() => {
            reconnectTimer = null;
            connect();
          }, 2000);
        }
      };
    };

    connect();

    return () => {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
      if (eventSource) {
        eventSource.close();
      }
    };
  }, []);

  const logout = async () => {
    try {
      await apiCall(API_CONFIG.ENDPOINTS.AUTH_LOGOUT, {
        method: "POST",
      });
    } catch (error) {
    } finally {
      window.location.href = "/login";
    }
  };

  const handleThemeToggle = () => {
    const newTheme = isDark ? "emerald" : "dark";
    setTheme(newTheme);
    setIsDark(!isDark);
    localStorage.setItem("theme", newTheme);
    window.dispatchEvent(
      new CustomEvent("themeChange", { detail: { theme: newTheme } }),
    );
  };

  const handleNavigate = (path: string) => {
    navigate(path);
    setSearchValue("");
    setShowResults(false);
  };

  const getIconForModule = (module: string) => {
    const icons: Record<string, React.ReactNode> = {
      Usuarios: (
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
          />
        </svg>
      ),
      Expediente: (
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
      ),
      Archivo: (
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z"
          />
        </svg>
      ),
    };

    return (
      icons[module] || (
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13 10V3L4 14h7v7l9-11h-7z"
          />
        </svg>
      )
    );
  };

  return (
    <header className="navbar bg-base-100 border-b border-base-300 shadow-sm sticky top-0 z-50 select-none px-4 h-16">
      {/* Drawer button */}
      <div className="flex-none">
        <label
          htmlFor="my-drawer"
          className="btn btn-ghost btn-square hover:bg-base-200"
          aria-label="Abrir menú"
        >
          <svg
            className="w-6 h-6 text-base-content"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 6h16M4 12h16M4 18h16"
            />
          </svg>
        </label>
      </div>

      {/* Logo / Title */}
      <div className="flex-1">
        <Link
          to="/"
          className="text-xl font-bold text-base-content px-3 py-2 rounded-lg hover:bg-base-200 transition-colors inline-block"
        >
          Corpochivor
        </Link>
      </div>

      {/* Right side actions */}
      <div className="flex-none">
        <div className="flex items-center gap-2">
          {/* Search input with dropdown */}
          <div
            className="form-control hidden md:block relative"
            ref={searchRef}
          >
            <div className="relative">
              <input
                type="text"
                placeholder="Buscar acceso rápido..."
                value={searchValue}
                onChange={(e) => setSearchValue(e.target.value)}
                onFocus={() => searchValue && setShowResults(true)}
                className="input input-sm input-bordered w-48 lg:w-64 pr-10"
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
                  <div className="text-xs font-semibold text-base-content/50 px-3 py-2">
                    Accesos rápidos ({filteredPermissions.length})
                  </div>
                  {filteredPermissions.map((perm, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleNavigate(perm.path)}
                      className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-base-200 rounded-lg transition-colors text-left group"
                    >
                      <div className="flex-shrink-0 w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-primary-content transition-colors">
                        {getIconForModule(perm.module)}
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
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 5l7 7-7 7"
                        />
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

          {/* Theme toggle */}
          <div
            className="tooltip tooltip-bottom"
            data-tip={isDark ? "Modo claro" : "Modo oscuro"}
          >
            <label className="swap swap-rotate btn btn-ghost btn-circle btn-sm">
              <input
                type="checkbox"
                checked={isDark}
                onChange={handleThemeToggle}
                aria-label="Cambiar tema"
              />

              {/* Sun icon */}
              <svg
                className="swap-off w-5 h-5 fill-warning"
                viewBox="0 0 24 24"
              >
                <circle cx="12" cy="12" r="5" />
                <line
                  x1="12"
                  y1="1"
                  x2="12"
                  y2="3"
                  stroke="currentColor"
                  strokeWidth="2"
                />
                <line
                  x1="12"
                  y1="21"
                  x2="12"
                  y2="23"
                  stroke="currentColor"
                  strokeWidth="2"
                />
                <line
                  x1="4.22"
                  y1="4.22"
                  x2="5.64"
                  y2="5.64"
                  stroke="currentColor"
                  strokeWidth="2"
                />
                <line
                  x1="18.36"
                  y1="18.36"
                  x2="19.78"
                  y2="19.78"
                  stroke="currentColor"
                  strokeWidth="2"
                />
                <line
                  x1="1"
                  y1="12"
                  x2="3"
                  y2="12"
                  stroke="currentColor"
                  strokeWidth="2"
                />
                <line
                  x1="21"
                  y1="12"
                  x2="23"
                  y2="12"
                  stroke="currentColor"
                  strokeWidth="2"
                />
                <line
                  x1="4.22"
                  y1="19.78"
                  x2="5.64"
                  y2="18.36"
                  stroke="currentColor"
                  strokeWidth="2"
                />
                <line
                  x1="18.36"
                  y1="5.64"
                  x2="19.78"
                  y2="4.22"
                  stroke="currentColor"
                  strokeWidth="2"
                />
              </svg>

              {/* Moon icon */}
              <svg className="swap-on w-5 h-5 fill-info" viewBox="0 0 24 24">
                <path d="M21.64 13a9 9 0 11-9.64-9.64A7 7 0 0021.64 13z" />
              </svg>
            </label>
          </div>

          {/* Notifications - siempre mostrar, incluso sin notificaciones */}
          {notification !== null && (
            <Notifications
              notifications={notification}
              onUpdate={setNotification}
            />
          )}

          {/* Profile dropdown */}
          <div className="dropdown dropdown-end">
            <div
              tabIndex={0}
              role="button"
              className="btn btn-ghost btn-circle avatar hover:ring-2 hover:ring-success transition-all"
              aria-label="Menú de usuario"
            >
              <div className="w-9 rounded-full overflow-hidden ring-1 ring-base-300">
                <ImgProfile />
              </div>
            </div>
            <ul
              tabIndex={0}
              className="menu menu-sm dropdown-content bg-base-100 rounded-lg mt-3 w-52 p-2 shadow-lg border border-base-300"
            >
              <li className="menu-title">
                <span className="text-xs font-semibold text-base-content/70">
                  Mi cuenta
                </span>
              </li>
              <li>
                <Link className="flex items-center gap-3 py-2" to="/profile">
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                    />
                  </svg>
                  Mi perfil
                </Link>
              </li>
              <div className="divider my-1"></div>
              <li>
                <a
                  onClick={logout}
                  className="flex items-center gap-3 py-2 text-error hover:bg-error/10"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                    />
                  </svg>
                  Cerrar sesión
                </a>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </header>
  );
}
