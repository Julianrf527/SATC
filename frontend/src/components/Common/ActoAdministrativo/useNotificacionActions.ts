import { useState } from "react";
import { apiCall, formatApiErrorDetail } from "../../../utils/api";
import type {
  ActoAdministrativo,
  InvolucradoNotificacion,
} from "../../../types/sancionatorioApp";
import type {
  ActoAdminEndpoints,
  ActoAdminOrEmpty,
  ActoAdminSaveResult,
  NotificacionFormData,
  SetToast,
} from "./actoAdminConfig";

type Params = {
  expedienteId: number;
  apiEndpoints: ActoAdminEndpoints;
  localActoAdmin: ActoAdminOrEmpty;
  setLocalActoAdmin: (actoAdmin: ActoAdminOrEmpty) => void;
  hasActoAdmin: boolean;
  isNotificacion: boolean;
  setToast: SetToast;
  onActoAdminUpdate?: (actoAdmin: ActoAdministrativo) => void;
};

/** Estado y CRUD de las notificaciones asociadas al acto administrativo. */
export function useNotificacionActions({
  expedienteId,
  apiEndpoints,
  localActoAdmin,
  setLocalActoAdmin,
  hasActoAdmin,
  isNotificacion,
  setToast,
  onActoAdminUpdate,
}: Params) {
  const [showNotificacionModal, setShowNotificacionModal] = useState(false);
  const [editingNotificacion, setEditingNotificacion] =
    useState<InvolucradoNotificacion | null>(null);

  const handleAddNotificacion = () => {
    setEditingNotificacion(null);
    setShowNotificacionModal(true);
  };

  const handleEditNotificacion = (notificacion: InvolucradoNotificacion) => {
    setEditingNotificacion(notificacion);
    setShowNotificacionModal(true);
  };

  const handleSaveNotificacion = async (
    notificationData: NotificacionFormData,
  ): Promise<ActoAdminSaveResult> => {
    const isEditing = editingNotificacion !== null;

    try {
      if (!hasActoAdmin || !("id" in localActoAdmin)) {
        return { ok: false, error: "No hay acto administrativo" };
      }

      const actoAdminCasted = localActoAdmin as ActoAdministrativo;

      const documentoCitacionId =
        notificationData.documento_citacion_id ??
        editingNotificacion?.documento_citacion_id;

      const documentoNotificacionId =
        notificationData.documento_notificacion_id ??
        editingNotificacion?.documento_notificacion_id ??
        undefined;

      const involucradoId =
        notificationData.involucrado_id ?? editingNotificacion?.involucrado_id;

      if (!documentoCitacionId) {
        return {
          ok: false,
          error:
            "Debe existir documento de citación para guardar la notificación",
        };
      }

      if (notificationData.notificacion_exitosa && !documentoNotificacionId) {
        return {
          ok: false,
          error:
            "Debe existir documento de notificación cuando la notificación es exitosa",
        };
      }

      if (!isEditing && !involucradoId) {
        return { ok: false, error: "Debe seleccionar un involucrado" };
      }

      const endpoint = isEditing
        ? `${apiEndpoints.notificacion.base}/${editingNotificacion!.id}`
        : apiEndpoints.notificacion.base;

      const method = isEditing ? "PUT" : "POST";

      const payload = new FormData();
      payload.append("expediente_id", String(expedienteId));
      payload.append("acto_admin_id", String(actoAdminCasted.id));
      payload.append("numerado", String(notificationData.numerado));
      payload.append("fecha_numerado", notificationData.fecha_numerado);
      payload.append(
        "fecha_envio_citacion",
        notificationData.fecha_envio_citacion,
      );
      payload.append(
        "fecha_constancia_citacion",
        notificationData.fecha_constancia_citacion || "",
      );
      payload.append(
        "notificacion_exitosa",
        String(notificationData.notificacion_exitosa),
      );
      payload.append("documento_citacion_id", String(documentoCitacionId));

      if (involucradoId) {
        payload.append("involucrado_id", String(involucradoId));
      }

      if (documentoNotificacionId) {
        payload.append(
          "documento_notificacion_id",
          String(documentoNotificacionId),
        );
      }

      if (notificationData.tipo_notificacion_id) {
        payload.append(
          "tipo_notificacion_id",
          String(notificationData.tipo_notificacion_id),
        );
      }

      if (notificationData.fecha_notificacion) {
        payload.append("fecha_notificacion", notificationData.fecha_notificacion);
      }

      const res = await apiCall(endpoint, {
        method,
        body: payload,
      });

      if (!res.ok) {
        const defaultMessage = isEditing
          ? "Error al actualizar notificación"
          : "Error al crear notificación";
        const errorMessage = res.detail
          ? formatApiErrorDetail(res.detail, defaultMessage)
          : res.message || defaultMessage;

        return { ok: false, error: errorMessage };
      }

      if (!res.data) {
        return {
          ok: false,
          error: "No se recibieron datos del servidor",
        };
      }

      const currentActo = localActoAdmin as ActoAdministrativo;

      const currentNotificacion = currentActo.notificacion || {
        id: 0,
        fecha_creacion: new Date().toISOString(),
        involucrados: [],
      };
      let updatedInvolucrados = Array.isArray(currentNotificacion.involucrados)
        ? [...currentNotificacion.involucrados]
        : [];

      if (isEditing) {
        updatedInvolucrados = updatedInvolucrados.map((inv) =>
          inv.id === res.data.id ? res.data : inv,
        );
      } else {
        updatedInvolucrados.push(res.data);
      }

      const updatedActoAdmin = {
        ...currentActo,
        notificacion: {
          ...currentNotificacion,
          involucrados: updatedInvolucrados,
        },
      };

      setLocalActoAdmin(updatedActoAdmin);
      if (onActoAdminUpdate) onActoAdminUpdate(updatedActoAdmin);

      setToast({
        id: Date.now(),
        message: isEditing
          ? "Notificación actualizada exitosamente"
          : "Notificación creada exitosamente",
        type: "success",
      });

      return { ok: true };
    } catch (e) {
      const errorMsg =
        e instanceof Error
          ? e.message
          : "Error de conexión al guardar notificación";
      return { ok: false, error: errorMsg };
    }
  };

  const handleDeleteNotificacion = async (invNotificacionId: number) => {
    try {
      const res = await apiCall(
        apiEndpoints.notificacion.delete(invNotificacionId),
        {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ expediente_id: expedienteId }),
        },
      );

      if (res.ok) {
        const currentActo = localActoAdmin as ActoAdministrativo;
        const currentNotificacion = currentActo.notificacion!;

        const updatedInvolucrados = Array.isArray(
          currentNotificacion.involucrados,
        )
          ? currentNotificacion.involucrados.filter(
              (inv) => inv.id !== invNotificacionId,
            )
          : [];

        const updatedActoAdmin = {
          ...currentActo,
          notificacion: {
            ...currentNotificacion,
            involucrados: updatedInvolucrados,
          },
        };

        setLocalActoAdmin(updatedActoAdmin);
        if (onActoAdminUpdate) onActoAdminUpdate(updatedActoAdmin);

        setToast({
          id: Date.now(),
          message: "Notificación eliminada exitosamente",
          type: "success",
        });
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al eliminar notificación",
          type: "error",
        });
      }
    } catch (e) {
      setToast({
        id: Date.now(),
        message: "Error al eliminar notificación",
        type: "error",
      });
    }
  };

  const getYaNotificados = (): number[] => {
    if (!hasActoAdmin || !isNotificacion) return [];
    const acto = localActoAdmin as ActoAdministrativo;
    if (!acto.notificacion) return [];
    if (!Array.isArray(acto.notificacion.involucrados)) return [];
    return acto.notificacion.involucrados
      .filter((inv) => inv && typeof inv.involucrado_id !== "undefined")
      .map((inv) => inv.involucrado_id);
  };

  const getNotificacionesExistentes = (): InvolucradoNotificacion[] => {
    if (!hasActoAdmin || !isNotificacion) return [];
    const acto = localActoAdmin as ActoAdministrativo;
    if (!acto.notificacion) return [];
    if (!Array.isArray(acto.notificacion.involucrados)) return [];
    return acto.notificacion.involucrados;
  };

  return {
    showNotificacionModal,
    setShowNotificacionModal,
    editingNotificacion,
    setEditingNotificacion,
    handleAddNotificacion,
    handleEditNotificacion,
    handleSaveNotificacion,
    handleDeleteNotificacion,
    getYaNotificados,
    getNotificacionesExistentes,
  };
}
