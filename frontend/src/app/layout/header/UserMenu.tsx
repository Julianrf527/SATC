import { Link } from "react-router-dom";
import { useLogoutMutation } from "../../api/auth";
import ImgProfile from "./ImgProfile";

/** Avatar + desplegable "Mi cuenta" (perfil y cerrar sesión). */
export default function UserMenu() {
  const logout = useLogoutMutation();

  return (
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
          <span className="text-xs font-semibold text-base-content/70">Mi cuenta</span>
        </li>
        <li>
          <Link className="flex items-center gap-3 py-2" to="/profile">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
            onClick={() => logout.mutate()}
            className="flex items-center gap-3 py-2 text-error hover:bg-error/10"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
  );
}
