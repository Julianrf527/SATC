import { useState } from "react";
import CardNotification from "./CardNotification";
import { apiCall, API_CONFIG } from "../../utils/api";

type Notification = {
  id: number;
  mensaje: string;
  id_vinculada: string;
  tipo: string;
};

type Props = {
  notification: Notification[];
  userId: number;
};

// Mapeo de tipos a títulos
const NOTIFICATION_CONFIG: Record<string, { title: string }> = {
  documento: { title: "Notificación de Documento" },
  expediente: { title: "Asignación de expediente" },
  licencia: { title: "Vinculación a licencia" },
};

export default function Notifications({
  notification: initialNotification,
  userId,
}: Props) {
  const [notification, setNotification] = useState(initialNotification);
  const [isDeletingAll, setIsDeletingAll] = useState(false);

  const onRemove = (id: number) => {
    setNotification((prev) => prev.filter((noti) => noti.id !== id));
  };

  const getNotificationTitle = (tipo: string): string => {
    return NOTIFICATION_CONFIG[tipo]?.title || "Notificación";
  };

  const handleMarkAllAsRead = async () => {
    setIsDeletingAll(true);
    try {
      const res = await apiCall(
        API_CONFIG.ENDPOINTS.NOTIFICATION_DELETE_ALL(userId),
        {
          method: "DELETE",
        }
      );

      if (res.ok) {
        setNotification([]);
        console.log(`${res.count} notificaciones eliminadas`);
      } else {
        console.error(res.detail || "Error al eliminar notificaciones");
      }
    } catch (error) {
      console.error("Error al marcar todas como leídas:", error);
    } finally {
      setIsDeletingAll(false);
    }
  };

  return (
    <div className="dropdown dropdown-end">
      <div
        tabIndex={0}
        role="button"
        className="btn btn-ghost btn-circle hover:bg-base-200 transition-colors relative"
      >
        <div className="indicator">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
            />
          </svg>
          {notification.length > 0 && (
            <span className="badge badge-sm badge-error text-white indicator-item animate-pulse">
              {notification.length > 99 ? "99+" : notification.length}
            </span>
          )}
        </div>
      </div>

      <div
        tabIndex={0}
        className="card card-compact dropdown-content bg-base-100 z-[1] mt-3 w-96 shadow-2xl border border-base-300 rounded-2xl overflow-hidden"
      >
        {/* Header del dropdown */}
        <div className="px-5 py-4 bg-gradient-to-r from-base-200 to-base-100 border-b border-base-300">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold text-base text-base-content">
                Notificaciones
              </h3>
              <p className="text-xs text-base-content/60 mt-0.5">
                {notification.length === 0
                  ? "No tienes notificaciones pendientes"
                  : `${notification.length} ${
                      notification.length === 1
                        ? "notificación pendiente"
                        : "notificaciones pendientes"
                    }`}
              </p>
            </div>

            {/* Ícono decorativo - solo cuando hay notificaciones */}
            {notification.length > 0 && (
              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                <svg
                  className="w-5 h-5 text-primary"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                  />
                </svg>
              </div>
            )}
          </div>
        </div>

        {/* Cuerpo con las notificaciones - solo se muestra si hay notificaciones */}
        {notification.length > 0 && (
          <>
            <div className="max-h-[32rem] overflow-y-auto p-3 space-y-2">
              {notification.map((noti) => (
                <CardNotification
                  key={noti.id}
                  idNotification={noti.id}
                  title={getNotificationTitle(noti.tipo)}
                  body={noti.mensaje}
                  idVinculada={noti.id_vinculada}
                  tipo={noti.tipo}
                  onRemove={() => onRemove(noti.id)}
                />
              ))}
            </div>

            {/* Footer con botón de marcar todas como leídas */}
            <div className="px-4 py-3 bg-base-200/50 border-t border-base-300">
              <button
                className="text-xs text-primary hover:text-primary-focus font-medium transition-colors flex items-center gap-1.5 mx-auto disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={handleMarkAllAsRead}
                disabled={isDeletingAll}
              >
                {isDeletingAll ? (
                  <>
                    <span className="loading loading-spinner loading-xs"></span>
                    <span>Eliminando...</span>
                  </>
                ) : (
                  <>
                    <svg
                      className="w-3.5 h-3.5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                    <span>Marcar todas como leídas</span>
                  </>
                )}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
