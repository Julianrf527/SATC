import { useState } from "react";
import { apiCall, formatApiErrorDetail } from "../../../utils/api";
import type { ActoAdministrativo } from "../../../types/sancionatorioApp";
import type {
  ActoAdminEndpoints,
  ActoAdminOrEmpty,
  ActoAdminFormData,
  ActoAdminSaveResult,
  ActoAdminStageBinding,
  SetToast,
} from "./actoAdminConfig";

type Params = {
  expedienteId: number;
  actoAdmin: ActoAdminOrEmpty;
  etapaId: number;
  apiEndpoints: ActoAdminEndpoints;
  stageBinding?: ActoAdminStageBinding;
  nivelAuxiliar?: boolean | null;
  customDeleteHandler?: () => Promise<void>;
  setToast: SetToast;
  setExistActoAdmin?: (exist: boolean) => void;
  onActoAdminUpdate?: (actoAdmin: ActoAdministrativo) => void;
};

/** Estado local del acto administrativo + CRUD del acto y de su comunicación. */
export function useActoAdminActions({
  expedienteId,
  actoAdmin,
  etapaId,
  apiEndpoints,
  stageBinding,
  nivelAuxiliar = null,
  customDeleteHandler,
  setToast,
  setExistActoAdmin,
  onActoAdminUpdate,
}: Params) {
  const [localActoAdmin, setLocalActoAdmin] = useState<ActoAdminOrEmpty>(
    actoAdmin,
  );
  const [showActoModal, setShowActoModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showComunicacionModal, setShowComunicacionModal] = useState(false);
  const [editingComunicacion, setEditingComunicacion] = useState(false);

  const hasActoAdmin = localActoAdmin && Object.keys(localActoAdmin).length > 1;

  const handleSaveActoAdmin = async (
    actoData: ActoAdminFormData,
  ): Promise<ActoAdminSaveResult> => {
    try {
      const isEditing = hasActoAdmin && "id" in localActoAdmin;
      const endpoint = isEditing
        ? apiEndpoints.actoAdmin.update(
            (localActoAdmin as ActoAdministrativo).id,
          )
        : apiEndpoints.actoAdmin.create;

      const method = isEditing ? "PUT" : "POST";

      // Preparar los datos finales con naming compatible con backend (FormData)
      const finalData = {
        ...actoData,
        expediente_id: expedienteId,
        etapa_id: etapaId,
      };

      // En edición, si no se sube nuevo documento, conservar el documento existente.
      if (
        isEditing &&
        (!finalData.documento_acto_id ||
          Number.isNaN(finalData.documento_acto_id)) &&
        "documento_acto_administrativo_id" in
          (localActoAdmin as ActoAdministrativo)
      ) {
        finalData.documento_acto_id = (
          localActoAdmin as ActoAdministrativo
        ).documento_acto_administrativo_id;
      }

      // Manejar nivel_auxiliar con prioridad
      if (
        finalData.nivel_auxiliar === null ||
        finalData.nivel_auxiliar === undefined
      ) {
        let nivel: boolean | null | undefined = undefined;

        // Prioridad 1: nivelAuxiliar prop
        if (nivelAuxiliar !== null && nivelAuxiliar !== undefined) {
          nivel = nivelAuxiliar;
        }
        // Prioridad 2: localActoAdmin
        else if (hasActoAdmin && "nivel_auxiliar" in localActoAdmin) {
          nivel = (localActoAdmin as ActoAdministrativo).nivel_auxiliar;
        }
        // Prioridad 3: actoAdmin prop
        else if (actoAdmin && "nivel_auxiliar" in actoAdmin) {
          nivel = (actoAdmin as ActoAdministrativo).nivel_auxiliar;
        }

        if (nivel !== null && nivel !== undefined) {
          finalData.nivel_auxiliar = nivel;
        }
      }

      const payload = new FormData();
      payload.append("expediente_id", String(finalData.expediente_id));
      if (stageBinding?.type?.startsWith("etapa_san_")) {
        // Las etapas de sancionatorio se referencian por etapa_tipo + etapa_ref_id.
        payload.append(
          "etapa_tipo",
          stageBinding.type.replace("etapa_san_", "etapa_"),
        );
        payload.append("etapa_ref_id", String(stageBinding.id));
      } else if (stageBinding?.type === "etapa") {
        payload.append("etapa_id", String(stageBinding.id));
      } else if (stageBinding?.type === "etapa_concepto") {
        payload.append("etapa_concepto_id", String(stageBinding.id));
      } else if (stageBinding?.type === "etapa_cierre") {
        payload.append("etapa_cierre_id", String(stageBinding.id));
      } else if (stageBinding?.type === "medida_preventiva") {
        payload.append("medida_preventiva_id", String(stageBinding.id));
      } else {
        payload.append("etapa_id", String(finalData.etapa_id));
      }
      payload.append("tipo_acto", finalData.tipo_acto);
      payload.append("numerado", String(finalData.numerado));
      payload.append("fecha_numerado", finalData.fecha_numerado);

      if (finalData.documento_acto_id) {
        payload.append(
          "documento_acto_administrativo_id",
          String(finalData.documento_acto_id),
        );
      } else if (!isEditing) {
        // En creación, el documento es requerido
        return { ok: false, error: "Debe seleccionar un documento PDF" };
      }

      if (
        !stageBinding &&
        finalData.nivel_auxiliar !== null &&
        finalData.nivel_auxiliar !== undefined
      ) {
        payload.append("nivel_auxiliar", String(finalData.nivel_auxiliar));
      }

      const res = await apiCall(endpoint, {
        method,
        body: payload,
      });

      if (res.ok) {
        const updatedActoAdmin = res.data;

        // Preservar notificaciones y comunicaciones existentes al actualizar
        const mergedActoAdmin =
          isEditing && hasActoAdmin
            ? {
                ...updatedActoAdmin,
                notificacion:
                  (localActoAdmin as ActoAdministrativo).notificacion ||
                  updatedActoAdmin.notificacion,
                comunicacion:
                  (localActoAdmin as ActoAdministrativo).comunicacion ||
                  updatedActoAdmin.comunicacion,
              }
            : updatedActoAdmin;

        setLocalActoAdmin(mergedActoAdmin);

        if (onActoAdminUpdate) onActoAdminUpdate(mergedActoAdmin);
        if (setExistActoAdmin) setExistActoAdmin(true);

        setToast({
          id: Date.now(),
          message: isEditing
            ? "Acto administrativo actualizado"
            : "Acto administrativo creado",
          type: "success",
        });

        return { ok: true };
      } else {
        const errorMessage = formatApiErrorDetail(
          res.detail,
          "Error al guardar acto administrativo",
        );
        return { ok: false, error: errorMessage };
      }
    } catch (e) {
      return { ok: false, error: "Error al guardar acto administrativo" };
    }
  };

  const handleDeleteActoAdmin = async () => {
    try {
      if (!hasActoAdmin || !("id" in localActoAdmin)) return;

      if (customDeleteHandler) {
        await customDeleteHandler();
        setShowDeleteModal(false);
        return;
      }

      const res = await apiCall(
        apiEndpoints.actoAdmin.delete((localActoAdmin as ActoAdministrativo).id),
        { method: "DELETE" },
      );

      if (res.ok) {
        setLocalActoAdmin({});
        if (onActoAdminUpdate) onActoAdminUpdate({} as ActoAdministrativo);
        if (setExistActoAdmin) setExistActoAdmin(false);

        setToast({
          id: Date.now(),
          message: "Acto administrativo eliminado",
          type: "success",
        });
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al eliminar acto administrativo",
          type: "error",
        });
      }
    } catch (e) {
      setToast({
        id: Date.now(),
        message: "Error al eliminar acto administrativo",
        type: "error",
      });
    } finally {
      setShowDeleteModal(false);
    }
  };

  const handleAddComunicacion = () => {
    setEditingComunicacion(false);
    setShowComunicacionModal(true);
  };

  const handleEditComunicacion = () => {
    setEditingComunicacion(true);
    setShowComunicacionModal(true);
  };

  const handleComunicacionSuccess = (updatedComunicacion: any) => {
    setShowComunicacionModal(false);
    setEditingComunicacion(false);

    const updatedActoAdmin = {
      ...(localActoAdmin as ActoAdministrativo),
      comunicacion: updatedComunicacion,
    };

    setLocalActoAdmin(updatedActoAdmin);
    if (onActoAdminUpdate) onActoAdminUpdate(updatedActoAdmin);

    setToast({
      id: Date.now(),
      message: editingComunicacion
        ? "Comunicación actualizada exitosamente"
        : "Comunicación agregada exitosamente",
      type: "success",
    });
  };

  const handleComunicacionDeleted = () => {
    const updatedActoAdmin: ActoAdministrativo = {
      ...(localActoAdmin as ActoAdministrativo),
      comunicacion: null,
    };
    setLocalActoAdmin(updatedActoAdmin);
    if (onActoAdminUpdate) onActoAdminUpdate(updatedActoAdmin);
  };

  return {
    localActoAdmin,
    setLocalActoAdmin,
    hasActoAdmin,
    showActoModal,
    setShowActoModal,
    showDeleteModal,
    setShowDeleteModal,
    showComunicacionModal,
    setShowComunicacionModal,
    editingComunicacion,
    setEditingComunicacion,
    handleSaveActoAdmin,
    handleDeleteActoAdmin,
    handleAddComunicacion,
    handleEditComunicacion,
    handleComunicacionSuccess,
    handleComunicacionDeleted,
  };
}
