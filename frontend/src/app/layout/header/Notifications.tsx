import { useClearNotificationsMutation } from "../../api/notifications";
import NotificationRow from "./NotificationRow";
import type { Notification } from "./notificationTypes";

type Props = {
  notifications: Notification[];
  /** Quita localmente una notificación ya borrada en el servidor. */
  onRemove: (id: number) => void;
  /** Vacía la lista local tras "Leer todas". */
  onClear: () => void;
};

export default function Notifications({ notifications, onRemove, onClear }: Props) {
  const limpiar = useClearNotificationsMutation();
  const clearing = limpiar.isPending;

  const handleClearAll = () => limpiar.mutate(undefined, { onSuccess: onClear });

  const count = notifications.length;

  return (
    <div className="dropdown dropdown-end">
      {/* Bell button */}
      <div tabIndex={0} role="button" className="btn btn-ghost btn-circle btn-sm hover:bg-base-200 relative">
        <div className="indicator">
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
              d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
            />
          </svg>
          {count > 0 && (
            <span className="badge badge-xs badge-error text-white indicator-item">
              {count > 9 ? "9+" : count}
            </span>
          )}
        </div>
      </div>

      {/* Panel */}
      <div
        tabIndex={0}
        className="dropdown-content mt-2 w-80 bg-base-100 rounded-xl shadow-xl border border-base-300 overflow-hidden z-[100]"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-3 py-2.5 border-b border-base-300 bg-base-200/50">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-base-content/60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
              />
            </svg>
            <span className="text-sm font-semibold text-base-content">
              Notificaciones
            </span>
            {count > 0 && (
              <span className="badge badge-sm badge-neutral">{count}</span>
            )}
          </div>
          {count > 0 && (
            <button
              onClick={handleClearAll}
              disabled={clearing}
              className="btn btn-ghost btn-xs gap-1 text-base-content/60 hover:text-base-content"
              title="Marcar todas como leídas"
            >
              {clearing ? (
                <span className="loading loading-spinner loading-xs" />
              ) : (
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
              )}
              <span className="text-[11px]">Leer todas</span>
            </button>
          )}
        </div>

        {/* List */}
        {count === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-base-content/60">
            <svg className="w-10 h-10 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="text-xs">Sin notificaciones</p>
          </div>
        ) : (
          <div className="max-h-72 overflow-y-auto divide-y divide-base-300/50">
            {notifications.map((noti) => (
              <NotificationRow
                key={noti.id}
                noti={noti}
                onRemove={() => onRemove(noti.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
