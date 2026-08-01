import { apiCall, API_CONFIG } from "../../utils/api";
import { useNavigate } from "react-router-dom";
import { useState } from "react";

type Props = {
  idNotification: number;
  title: string;
  body: string;
  idVinculada: string;
  tipo: string;
  onRemove: () => void;
};

export default function CardNotification({
  idNotification,
  title,
  body,
  idVinculada,
  tipo,
  onRemove,
}: Props) {
  const [isDeleting, setIsDeleting] = useState(false);
  const navigate = useNavigate();

  const typeConfig = NOTIFICATION_TYPES[
    tipo as keyof typeof NOTIFICATION_TYPES
  ] || {
    icon: (
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
          d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
        />
      </svg>
    ),
    color: "info",
    hasRoute: false,
    route: null,
    label: "Notificación",
  };

  const onDelete = async () => {
    setIsDeleting(true);
    try {
      const res = await apiCall(
        API_CONFIG.ENDPOINTS.NOTIFICATION_DELETE(idNotification),
        {
          method: "DELETE",
        }
      );

      if (res.ok) {
        onRemove();
      } else {
        setIsDeleting(false);
      }
    } catch (error) {
      setIsDeleting(false);
    }
  };

  const handleNavigate = () => {
    if (typeConfig.hasRoute && typeConfig.route) {
      const route = typeConfig.route(idVinculada);

      if (typeof route === "object" && "pathname" in route) {
        navigate(route.pathname, { state: route.state });
      } else {
        navigate(route);
      }
    }
  };

  const handleActionClick = () => {
    onDelete();
    handleNavigate();
  };

  return (
    <div className="bg-base-100 w-full shadow-sm rounded-xl border border-base-300 hover:shadow-md hover:border-base-content/20 transition-all duration-200">
      <div className="p-3">
        {/* Header con ícono, título y botón cerrar */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-start gap-2.5 flex-1 min-w-0">
            {/* Ícono dinámico según tipo */}
            <div
              className={`w-9 h-9 bg-${typeConfig.color}/10 rounded-xl flex items-center justify-center flex-shrink-0 ring-1 ring-${typeConfig.color}/20`}
            >
              <div className={`text-${typeConfig.color}`}>
                {typeConfig.icon}
              </div>
            </div>

            {/* Título y badge de tipo */}
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-semibold text-base-content leading-tight mb-1">
                {title}
              </h3>
              <div
                className={`badge badge-${typeConfig.color} badge-xs gap-1 badge-outline`}
              >
                <span className="text-[10px] font-medium">
                  {typeConfig.label}
                </span>
              </div>
            </div>
          </div>

          {/* Botón cerrar */}
          <button
            className="btn btn-ghost btn-xs btn-circle hover:bg-error/10 hover:text-error flex-shrink-0 transition-colors"
            title="Descartar notificación"
            onClick={onDelete}
            disabled={isDeleting}
          >
            {isDeleting ? (
              <span className="loading loading-spinner loading-xs"></span>
            ) : (
              <svg
                className="w-3.5 h-3.5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2.5}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            )}
          </button>
        </div>

        {/* Body del mensaje */}
        <p className="text-xs text-base-content/70 leading-relaxed mb-3 pl-11 line-clamp-2">
          {body}
        </p>

        {/* Footer con ID vinculada y botón de acción */}
        <div className="flex items-center justify-between pt-2.5 border-t border-base-300/50">
          <div className="flex items-center gap-1.5 text-base-content/50">
            <svg
              className="w-3 h-3"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14"
              />
            </svg>
            <span className="font-mono text-[10px] font-medium">
              {idVinculada}
            </span>
          </div>

          {/* Botón de acción solo si hay ruta configurada */}
          {typeConfig.hasRoute && (
            <button
              className={`btn btn-${typeConfig.color} btn-xs gap-1.5 text-white hover:scale-105 transition-transform`}
              title={`Ver ${typeConfig.label.toLowerCase()}`}
              onClick={handleActionClick}
              disabled={isDeleting}
            >
              <span className="text-xs font-medium">Ver detalle</span>
              <svg
                className="w-3 h-3"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2.5}
                  d="M13 7l5 5m0 0l-5 5m5-5H6"
                />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

const NOTIFICATION_TYPES = {
  documento: {
    icon: (
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
    color: "primary",
    hasRoute: true,
    route: (id: string) => ({
      pathname: "/document/manage",
      state: { documentoIdToSelect: id, timestamp: Date.now() },
    }),
    label: "Documento",
  },
  expediente: {
    icon: (
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
    color: "info",
    hasRoute: true,
    route: (id: string) => ({
      pathname: "/file/manage",
      state: { radicadoToSelect: id, timestamp: Date.now() },
    }),
    label: "Expediente",
  },
  licencia: {
    icon: (
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
          d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
        />
      </svg>
    ),
    color: "success",
    hasRoute: true,
    route: (id: string) => `/licencias/${id}`,
    label: "Licencia",
  },
  informe_tecnico: {
    icon: (
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
          d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
    ),
    color: "warning",
    hasRoute: false,
    route: null,
    label: "Informe Técnico",
  },
};
