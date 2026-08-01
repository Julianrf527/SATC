import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiCall, API_CONFIG } from "../../utils/api";

type Notification = {
  id: number;
  mensaje: string;
  id_vinculada: string;
  tipo: string;
};

type Props = {
  notifications: Notification[];
  onUpdate: (notifications: Notification[]) => void;
};

// Ruteo por tipo de notificación: a dónde navega cada una al hacer click.
const TYPE_CONFIG: Record<string, {
  label: string;
  dotClass: string;
  hasRoute: boolean;
  route?: (id: string) => { pathname: string; state: object } | string;
}> = {
  documento: {
    label: "Documento",
    dotClass: "bg-primary",
    hasRoute: true,
    route: (id) => ({
      pathname: "/document/manage",
      state: { documentoIdToSelect: id, timestamp: Date.now() },
    }),
  },
  expediente: {
    label: "Expediente",
    dotClass: "bg-info",
    hasRoute: true,
    route: (id) => ({
      pathname: "/file/manage",
      state: { radicadoToSelect: id, timestamp: Date.now() },
    }),
  },
  licencia: {
    label: "Licencia",
    dotClass: "bg-success",
    hasRoute: true,
    route: (id) => `/licencias/${id}`,
  },
  informe_tecnico: {
    label: "Informe",
    dotClass: "bg-warning",
    hasRoute: false,
  },
};

const DEFAULT_CONFIG = { label: "Aviso", dotClass: "bg-base-content/40", hasRoute: false };

function getConfig(tipo: string) {
  return TYPE_CONFIG[tipo] ?? DEFAULT_CONFIG;
}

function NotifRow({
  noti,
  onRemove,
}: {
  noti: Notification;
  onRemove: () => void;
}) {
  const navigate = useNavigate();
  const cfg = getConfig(noti.tipo);
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    setDeleting(true);
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.NOTIFICATION_DELETE(noti.id), {
        method: "DELETE",
      });
      if (res.ok) onRemove();
    } finally {
      setDeleting(false);
    }
  };

  const handleNavigate = () => {
    if (!cfg.hasRoute || !cfg.route) return;
    const route = cfg.route(noti.id_vinculada);
    if (typeof route === "object" && "pathname" in route) {
      navigate(route.pathname, { state: route.state });
    } else {
      navigate(route as string);
    }
    // delete after navigate so it disappears
    handleDelete();
  };

  return (
    <div className="flex items-start gap-2.5 px-3 py-2.5 hover:bg-base-200/60 transition-colors group">
      {/* dot */}
      <div className={`mt-1.5 w-2 h-2 rounded-full flex-shrink-0 ${cfg.dotClass}`} />

      {/* content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 mb-0.5">
          <span className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wide">
            {cfg.label}
          </span>
        </div>
        <p className="text-xs text-base-content/80 leading-relaxed line-clamp-2">
          {noti.mensaje}
        </p>
      </div>

      {/* actions */}
      <div className="flex items-center gap-0.5 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
        {cfg.hasRoute && (
          <button
            onClick={handleNavigate}
            className="btn btn-ghost btn-xs btn-circle"
            title="Ver detalle"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </button>
        )}
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="btn btn-ghost btn-xs btn-circle hover:text-error"
          title="Descartar"
        >
          {deleting ? (
            <span className="loading loading-spinner loading-xs" />
          ) : (
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
            </svg>
          )}
        </button>
      </div>
    </div>
  );
}

export default function Notifications({ notifications, onUpdate }: Props) {
  const [clearing, setClearing] = useState(false);

  const onRemove = (id: number) => {
    onUpdate(notifications.filter((n) => n.id !== id));
  };

  const handleClearAll = async () => {
    setClearing(true);
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.NOTIFICATION_DELETE_ALL, {
        method: "DELETE",
      });
      if (res.ok) onUpdate([]);
    } finally {
      setClearing(false);
    }
  };

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
            <span className="badge badge-xs badge-error text-white indicator-item animate-pulse">
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
          <div className="flex flex-col items-center justify-center py-8 text-base-content/40">
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
              <NotifRow
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
