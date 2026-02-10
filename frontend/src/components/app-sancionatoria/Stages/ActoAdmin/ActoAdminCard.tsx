import ComunicacionCard from "./ComunicacionCard";
import NotificacionesTable from "./NotificationesTable";
import { API_CONFIG } from "../../../../utils/api";
import type {
  Involved,
  TipoNotificacion,
  InvolucradoNotificacion,
  ActoAdminData
} from "../../../../types";

type TipoActo = "notificacion" | "comunicacion";



type Props = {
  actoAdmin: ActoAdminData;
  radicado: string;
  tipoActo: TipoActo;
  onEdit: () => void;
  onDelete: () => void;
  onAddComunicacion?: () => void;
  onEditComunicacion?: () => void;
  onComunicacionDeleted?: () => void;
  onAddNotificacion?: () => void;
  onEditNotificacion?: (notificacion: InvolucradoNotificacion) => void;
  onDeleteNotificacion?: (id: number) => void;
  onViewDocument: (url: string) => void;
  involucrados?: Involved[];
  tiposNotificacion?: TipoNotificacion[];
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  isEditable?: boolean;
};

export default function ActoAdminCard({
  actoAdmin,
  radicado,
  tipoActo,
  onEdit,
  onDelete,
  onAddComunicacion,
  onEditComunicacion,
  onComunicacionDeleted,
  onAddNotificacion,
  onEditNotificacion,
  onDeleteNotificacion,
  onViewDocument,
  involucrados = [],
  tiposNotificacion = [],
  setToast,
  isEditable = true,
}: Props) {
  const getTipoBadgeStyles = (tipo: string) => {
    const styles = {
      AUTO: "badge-success",
      RES: "badge-info",
    };
    return styles[tipo as keyof typeof styles] || "badge-ghost";
  };

  const formatDate = (fecha: string | null) => {
    if (!fecha) return "No registrada";
    const [year, month, day] = fecha.split("-");
    const meses = [
      "enero",
      "febrero",
      "marzo",
      "abril",
      "mayo",
      "junio",
      "julio",
      "agosto",
      "septiembre",
      "octubre",
      "noviembre",
      "diciembre",
    ];
    return `${parseInt(day)} de ${meses[parseInt(month) - 1]} de ${year}`;
  };

  const handleViewFile = () => {
    const BASE_URL = import.meta.env.VITE_API_URL;
    const url = `${BASE_URL}${API_CONFIG.ENDPOINTS.FILE_DOWNLOAD(
      actoAdmin.url_acto
    )}`;
    window.open(url, "_blank");
  };

  const isNotificacion = tipoActo === "notificacion";
  const isComunicacion = tipoActo === "comunicacion";

  const todosNotificados =
    isNotificacion &&
    involucrados.length > 0 &&
    Array.isArray(actoAdmin.notificacion?.involucrados) &&
    actoAdmin.notificacion.involucrados.length === involucrados.length;

  return (
    <div className="card bg-base-100 shadow-md border border-base-300 mb-4">
      <div className="card-body p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-bold">Acto Administrativo</h2>
          </div>

          {isEditable && (
            <div className="flex items-center gap-2">
              <button
                onClick={onEdit}
                className="btn btn-ghost btn-sm btn-square"
                title="Editar acto administrativo"
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
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                  />
                </svg>
              </button>

              <button
                onClick={onDelete}
                className="btn btn-ghost btn-sm btn-square text-error hover:bg-error/10"
                title="Eliminar acto administrativo"
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
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </button>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between gap-4 pb-4 border-b border-base-300">
          <div className="flex items-center gap-4">
            <span
              className={`badge badge-lg ${getTipoBadgeStyles(
                actoAdmin.tipo_acto
              )}`}
            >
              {actoAdmin.tipo_acto}
            </span>

            <span className="text-lg font-bold">
              {actoAdmin.numerado} del {formatDate(actoAdmin.fecha_numerado)}
            </span>
          </div>

          <button
            onClick={handleViewFile}
            className="btn btn-ghost btn-sm hover:bg-error/10"
            title="Ver documento PDF"
          >
            <svg
              className="w-8 h-8 text-error"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M15.5,15.5L13,19L11.5,15.5L8,14L11.5,12.5L13,9L14.5,12.5L18,14L15.5,15.5M13,3.5L17.5,8H13V3.5Z" />
            </svg>
          </button>
        </div>

        {isComunicacion && (
          <div className="mt-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base font-bold flex items-center gap-2">
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
                    d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                  />
                </svg>
                Comunicación
              </h3>

              {isEditable &&
                onAddComunicacion &&
                !actoAdmin.comunicacion?.id && (
                  <button
                    onClick={onAddComunicacion}
                    className="btn btn-success text-white btn-sm gap-2"
                    title="Agregar comunicación"
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
                        d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                      />
                    </svg>
                    Agregar Comunicación
                  </button>
                )}
            </div>
            <ComunicacionCard
              comunicacion={actoAdmin.comunicacion || null}
              radicado={radicado}
              onEdit={onEditComunicacion}
              onDeleted={onComunicacionDeleted}
              setToast={setToast}
              isEditable={isEditable}
            />
          </div>
        )}

        {isNotificacion && (
          <div className="mt-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base font-bold flex items-center gap-2">
                <svg
                  className="w-5 h-5 text-success"
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
                Notificaciones
                <span className="text-xs text-base-content/60 font-normal">
                  (
                  {Array.isArray(actoAdmin.notificacion?.involucrados)
                    ? actoAdmin.notificacion.involucrados.length
                    : 0}{" "}
                  de {involucrados.length})
                </span>
              </h3>

              {isEditable && (
                <>
                  {involucrados.length === 0 ? (
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-warning/10 border border-warning/20 rounded-lg">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="stroke-warning h-5 w-5"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                        />
                      </svg>
                      <span className="text-sm text-warning font-medium">
                        Agregue presuntos infractores
                      </span>
                    </div>
                  ) : todosNotificados ? (
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-success/10 border border-success/20 rounded-lg">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="stroke-success h-5 w-5"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                      <span className="text-sm text-success font-medium">
                        Todos notificados
                      </span>
                    </div>
                  ) : (
                    onAddNotificacion && (
                      <button
                        onClick={onAddNotificacion}
                        className="btn btn-success text-white btn-sm gap-2"
                        title="Agregar notificación"
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
                            d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                          />
                        </svg>
                        Agregar Notificación
                      </button>
                    )
                  )}
                </>
              )}
            </div>

            <NotificacionesTable
              notificaciones={
                Array.isArray(actoAdmin.notificacion?.involucrados)
                  ? actoAdmin.notificacion.involucrados
                  : []
              }
              involucrados={involucrados}
              tiposNotificacion={tiposNotificacion}
              onEdit={onEditNotificacion!}
              onDelete={onDeleteNotificacion!}
              onViewDocument={onViewDocument}
              isEditable={isEditable}
            />
          </div>
        )}
      </div>
    </div>
  );
}
