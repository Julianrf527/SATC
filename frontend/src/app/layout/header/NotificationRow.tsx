import { useNavigate } from "react-router-dom";
import { useDeleteNotificationMutation } from "../../api/notifications";
import { getNotificationConfig, type Notification } from "./notificationTypes";

type Props = {
  noti: Notification;
  onRemove: () => void;
};

export default function NotificationRow({ noti, onRemove }: Props) {
  const navigate = useNavigate();
  const cfg = getNotificationConfig(noti.tipo);
  const eliminar = useDeleteNotificationMutation();

  const handleDelete = () => eliminar.mutate(noti.id, { onSuccess: onRemove });

  const handleNavigate = () => {
    if (!cfg.route) return;
    const route = cfg.route(noti.id_vinculada);
    if (typeof route === "object") {
      navigate(route.pathname, { state: route.state });
    } else {
      navigate(route);
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
          <span className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wide">
            {cfg.label}
          </span>
        </div>
        <NotificationMessage mensaje={noti.mensaje} />
      </div>

      {/* actions */}
      <div className="flex items-center gap-0.5 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
        {cfg.route && (
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
          disabled={eliminar.isPending}
          className="btn btn-ghost btn-xs btn-circle hover:text-error"
          title="Descartar"
        >
          {eliminar.isPending ? (
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

/** Si el mensaje trae salto de línea, la primera línea va como título. */
function NotificationMessage({ mensaje }: { mensaje: string }) {
  if (!mensaje.includes("\n")) {
    return <p className="text-xs text-base-content/80 leading-relaxed">{mensaje}</p>;
  }
  const [primera, ...resto] = mensaje.split("\n");
  return (
    <>
      <p className="text-xs font-semibold text-base-content/90">{primera}</p>
      <p className="text-xs text-base-content/70 leading-relaxed">{resto.join(" ")}</p>
    </>
  );
}
