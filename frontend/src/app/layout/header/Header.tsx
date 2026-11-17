import { Link } from "react-router-dom";
import Notifications from "./Notifications";
import QuickSearch from "./QuickSearch";
import ThemeToggle from "./ThemeToggle";
import UserMenu from "./UserMenu";
import { useNotificationStream } from "./useNotificationStream";
import type { HeaderPermission } from "./quickSearchFilter";

type Props = {
  permission: HeaderPermission[];
};

export default function Header({ permission = [] }: Props) {
  const [notifications, setNotifications] = useNotificationStream();

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
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
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
          <QuickSearch permission={permission} />
          <ThemeToggle />

          {/* Campana: aparece tras el primer mensaje SSE (aunque venga vacío) */}
          {notifications !== null && (
            <Notifications
              notifications={notifications}
              onRemove={(id) =>
                setNotifications((prev) => prev && prev.filter((n) => n.id !== id))
              }
              onClear={() => setNotifications([])}
            />
          )}

          <UserMenu />
        </div>
      </div>
    </header>
  );
}
