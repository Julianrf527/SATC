import { useState } from "react";
import { apiCall, API_CONFIG } from "../../../../utils/api";
import type {
  ActoAdminData,
  Involved,
  TipoNotificacion,
  InvolucradoNotificacion,
} from "../../../../types";
import ActoAdminCard from "./ActoAdminCard";
import ActoAdminModal from "./ActoAdminModal";
import ConfirmDeleteModal from "./ConfirmDeleteModal";
import ComunicacionModal from "./ComunicacionModal";
import NotificacionModal from "./NotificationModal";

type TipoActo = "notificacion" | "comunicacion";

type Props = {
  radicado: string;
  idAuxiliar: number;
  actoAdmin: ActoAdminData | {};
  etapaId: number;
  tipoEtapa: string;
  tipoActo: TipoActo;
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  isEditable?: boolean;
  setExistActoAdmin?: (exist: boolean) => void;
  onActoAdminUpdate?: (actoAdmin: ActoAdminData) => void;
  involucrados?: Involved[];
  tiposNotificacion?: TipoNotificacion[];
  customDeleteHandler?: () => Promise<void>;
  nivelAuxiliar?: boolean | null;
};

export default function ActoAdmin({
  radicado,
  idAuxiliar,
  actoAdmin,
  etapaId,
  tipoEtapa,
  tipoActo,
  setToast,
  isEditable = true,
  setExistActoAdmin,
  onActoAdminUpdate,
  involucrados = [],
  tiposNotificacion = [],
  customDeleteHandler,
  nivelAuxiliar = null,
}: Props) {
  const [localActoAdmin, setLocalActoAdmin] = useState<ActoAdminData | {}>(
    actoAdmin
  );
  const [showActoModal, setShowActoModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showComunicacionModal, setShowComunicacionModal] = useState(false);
  const [showNotificacionModal, setShowNotificacionModal] = useState(false);
  const [editingComunicacion, setEditingComunicacion] = useState(false);
  const [editingNotificacion, setEditingNotificacion] =
    useState<InvolucradoNotificacion | null>(null);

  const hasActoAdmin = localActoAdmin && Object.keys(localActoAdmin).length > 1;
  const isNotificacion = tipoActo === "notificacion";
  const isComunicacion = tipoActo === "comunicacion";

  const handleSaveActoAdmin = async (
    formData: FormData
  ): Promise<{ ok: boolean; error?: string }> => {
    try {
      const isEditing = hasActoAdmin && "id" in localActoAdmin;
      const endpoint = isEditing
        ? API_CONFIG.ENDPOINTS.FILE_ACTO_ADMIN_UPDATE(
            (localActoAdmin as ActoAdminData).id
          )
        : API_CONFIG.ENDPOINTS.FILE_ACTO_ADMIN;

      const method = isEditing ? "PUT" : "POST";

      if (!formData.has("radicado_expediente"))
        formData.append("radicado_expediente", radicado);
      if (!formData.has("etapa_id"))
        formData.append("etapa_id", etapaId.toString());
      if (!formData.has("id_auxiliar"))
        formData.append("id_auxiliar", idAuxiliar.toString());
      if (!formData.has("tipo_etapa")) formData.append("tipo_etapa", tipoEtapa);

      // Manejar nivel_auxiliar con prioridad: FormData > Prop > localActoAdmin > actoAdmin
      if (!formData.has("nivel_auxiliar")) {
        let nivel: boolean | null | undefined = undefined;
        
        // Prioridad 1: nivelAuxiliar prop
        if (nivelAuxiliar !== null && nivelAuxiliar !== undefined) {
          nivel = nivelAuxiliar;
        }
        // Prioridad 2: localActoAdmin
        else if (hasActoAdmin && "nivel_auxiliar" in localActoAdmin) {
          nivel = (localActoAdmin as ActoAdminData).nivel_auxiliar;
        }
        // Prioridad 3: actoAdmin prop
        else if (actoAdmin && "nivel_auxiliar" in actoAdmin) {
          nivel = (actoAdmin as ActoAdminData).nivel_auxiliar;
        }
        
        if (nivel !== null && nivel !== undefined) {
          formData.append("nivel_auxiliar", nivel.toString());
        }
      }

      const res = await apiCall(endpoint, { method, body: formData });

      if (res.ok) {
        const updatedActoAdmin = res.data;
        setLocalActoAdmin(updatedActoAdmin);

        if (onActoAdminUpdate) onActoAdminUpdate(updatedActoAdmin);
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
        let errorMessage = "Error al guardar acto administrativo";

        if (res.detail) {
          if (typeof res.detail === "string") {
            errorMessage = res.detail;
          } else if (Array.isArray(res.detail)) {
            errorMessage = res.detail.map((err: any) => err.msg).join(", ");
          }
        }

        console.error("Error del backend:", res);
        return { ok: false, error: errorMessage };
      }
    } catch (e) {
      console.error("Error guardando acto administrativo:", e);
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
        API_CONFIG.ENDPOINTS.FILE_ACTO_ADMIN_DELETE(
          (localActoAdmin as ActoAdminData).id
        ),
        { method: "DELETE" }
      );

      if (res.ok) {
        setLocalActoAdmin({});
        if (onActoAdminUpdate) onActoAdminUpdate({} as ActoAdminData);
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
      console.error("Error eliminando acto administrativo:", e);
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
      ...(localActoAdmin as ActoAdminData),
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
    const updatedActoAdmin: ActoAdminData = {
      ...(localActoAdmin as ActoAdminData),
      comunicacion: null,
    };
    setLocalActoAdmin(updatedActoAdmin);
    if (onActoAdminUpdate) onActoAdminUpdate(updatedActoAdmin);
  };

  const handleAddNotificacion = () => {
    setEditingNotificacion(null);
    setShowNotificacionModal(true);
  };

  const handleEditNotificacion = (notificacion: InvolucradoNotificacion) => {
    setEditingNotificacion(notificacion);
    setShowNotificacionModal(true);
  };

  const handleSaveNotificacion = async (
    formData: FormData
  ): Promise<{ ok: boolean; error?: string }> => {
    const isEditing = editingNotificacion !== null;
    console.log("[handleSaveNotificacion] Modo:", isEditing ? "EDICIÓN" : "CREACIÓN");
    
    try {
      if (!hasActoAdmin || !("id" in localActoAdmin)) {
        console.error("[handleSaveNotificacion] No hay acto administrativo");
        return { ok: false, error: "No hay acto administrativo" };
      }

      const actoAdminCasted = localActoAdmin as ActoAdminData;
      let notificacionId: number;

      // Crear notificación base si no existe
      if (!actoAdminCasted.notificacion || !actoAdminCasted.notificacion.id) {
        console.log("[handleSaveNotificacion] Creando notificación base...");
        const notifFormData = new FormData();
        notifFormData.append("radicado", radicado);
        notifFormData.append("acto_admin_id", actoAdminCasted.id.toString());

        const notifRes = await apiCall(API_CONFIG.ENDPOINTS.FILE_NOTIFICACION, {
          method: "POST",
          body: notifFormData,
        });

        if (!notifRes.ok) {
          console.error("[handleSaveNotificacion] Error creando notificación base:", notifRes);
          return {
            ok: false,
            error: notifRes.detail || "Error al crear notificación base",
          };
        }

        if (!notifRes.data || !notifRes.data.id) {
          console.error("[handleSaveNotificacion] Notificación base sin ID");
          return {
            ok: false,
            error: "Error al crear notificación: ID no disponible",
          };
        }

        notificacionId = notifRes.data.id;
        console.log("[handleSaveNotificacion] Notificación base creada, ID:", notificacionId);

        const updatedActo = {
          ...actoAdminCasted,
          notificacion: { ...notifRes.data, involucrados: [] },
        };
        setLocalActoAdmin(updatedActo);
        if (onActoAdminUpdate) onActoAdminUpdate(updatedActo);
      } else {
        notificacionId = actoAdminCasted.notificacion.id;
        console.log("[handleSaveNotificacion] Usando notificación existente, ID:", notificacionId);
      }

      // Agregar datos comunes al FormData
      formData.append("notificacion_id", notificacionId.toString());
      formData.append("radicado", radicado);
      formData.append("id_auxiliar", idAuxiliar.toString());
      formData.append("tipo_etapa", tipoEtapa);

      // Determinar endpoint y método según si es edición o creación
      const endpoint = isEditing
        ? API_CONFIG.ENDPOINTS.FILE_INVOLUCRADO_NOTIFICACION_UPDATE(
            editingNotificacion!.id
          )
        : API_CONFIG.ENDPOINTS.FILE_INVOLUCRADO_NOTIFICACION;
      
      const method = isEditing ? "PUT" : "POST";
      
      console.log("[handleSaveNotificacion] Llamando endpoint:", endpoint);
      console.log("[handleSaveNotificacion] Método:", method);
      
      // Ejecutar la petición
      const res = await apiCall(endpoint, { method, body: formData });
      console.log("[handleSaveNotificacion] Respuesta completa:", res);

      // Verificar respuesta exitosa
      if (!res.ok) {
        console.error("[handleSaveNotificacion] Respuesta no exitosa:", res);
        let errorMessage = isEditing
          ? "Error al actualizar notificación"
          : "Error al crear notificación";

        if (res.detail) {
          if (typeof res.detail === "string") {
            errorMessage = res.detail;
          } else if (Array.isArray(res.detail)) {
            errorMessage = res.detail.map((err: any) => err.msg).join(", ");
          }
        } else if (res.message) {
          errorMessage = res.message;
        }

        return { ok: false, error: errorMessage };
      }

      // Verificar que llegó data
      if (!res.data) {
        console.error("[handleSaveNotificacion] Respuesta sin data:", res);
        return {
          ok: false,
          error: "No se recibieron datos del servidor",
        };
      }

      console.log("[handleSaveNotificacion] Data recibida:", res.data);

      // Actualizar estado local
      const currentActo = localActoAdmin as ActoAdminData;

      if (!currentActo.notificacion) {
        console.error("[handleSaveNotificacion] No existe notificación en acto actual");
        return { ok: false, error: "Error al actualizar notificación" };
      }

      const currentNotificacion = currentActo.notificacion;
      let updatedInvolucrados = Array.isArray(currentNotificacion.involucrados)
        ? [...currentNotificacion.involucrados]
        : [];

      if (isEditing) {
        console.log("[handleSaveNotificacion] Actualizando involucrado existente");
        updatedInvolucrados = updatedInvolucrados.map((inv) =>
          inv.id === res.data.id ? res.data : inv
        );
      } else {
        console.log("[handleSaveNotificacion] Agregando nuevo involucrado");
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

      console.log("[handleSaveNotificacion] Estado actualizado exitosamente");

      setToast({
        id: Date.now(),
        message: isEditing
          ? "Notificación actualizada exitosamente"
          : "Notificación creada exitosamente",
        type: "success",
      });

      console.log("[handleSaveNotificacion] Retornando ok: true");
      return { ok: true };
      
    } catch (e) {
      console.error("[handleSaveNotificacion] Excepción capturada:", e);
      const errorMsg = e instanceof Error ? e.message : "Error de conexión al guardar notificación";
      return { ok: false, error: errorMsg };
    }
  };

  const handleDeleteNotificacion = async (invNotificacionId: number) => {
    try {
      const res = await apiCall(
        API_CONFIG.ENDPOINTS.FILE_INVOLUCRADO_NOTIFICACION_DELETE(
          invNotificacionId
        ) + `?radicado=${radicado}`,
        { method: "DELETE" }
      );

      if (res.ok) {
        const currentActo = localActoAdmin as ActoAdminData;
        const currentNotificacion = currentActo.notificacion!;

        const updatedInvolucrados = Array.isArray(
          currentNotificacion.involucrados
        )
          ? currentNotificacion.involucrados.filter(
              (inv) => inv.id !== invNotificacionId
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
      console.error("Error eliminando notificación:", e);
      setToast({
        id: Date.now(),
        message: "Error al eliminar notificación",
        type: "error",
      });
    }
  };

  const handleViewDocument = (url: string) => {
    const BASE_URL = import.meta.env.VITE_API_URL;
    const fullUrl = `${BASE_URL}${API_CONFIG.ENDPOINTS.FILE_DOWNLOAD(url)}`;
    window.open(fullUrl, "_blank");
  };

  const getYaNotificados = (): number[] => {
    if (!hasActoAdmin || !isNotificacion) return [];
    const acto = localActoAdmin as ActoAdminData;
    if (!acto.notificacion) return [];
    if (!Array.isArray(acto.notificacion.involucrados)) return [];
    return acto.notificacion.involucrados
      .filter((inv) => inv && typeof inv.involucrado_id !== "undefined")
      .map((inv) => inv.involucrado_id);
  };

  const getNotificacionesExistentes = (): InvolucradoNotificacion[] => {
    if (!hasActoAdmin || !isNotificacion) return [];
    const acto = localActoAdmin as ActoAdminData;
    if (!acto.notificacion) return [];
    if (!Array.isArray(acto.notificacion.involucrados)) return [];
    return acto.notificacion.involucrados;
  };

  if (!hasActoAdmin) {
    if (!isEditable) {
      return (
        <div className="card bg-base-100 shadow-md border border-base-300">
          <div className="card-body">
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-base-200 rounded-full flex items-center justify-center mb-4 mx-auto">
                <svg
                  className="w-8 h-8 text-base-content/40"
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
              </div>
              <h3 className="text-lg font-medium text-base-content/70 mb-2">
                Sin acto administrativo
              </h3>
              <p className="text-base-content/60">
                No hay acto administrativo registrado para esta etapa
              </p>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="card bg-base-100 shadow-md border border-base-300">
        <div className="card-body">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
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
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
              </div>
              <div>
                <h3 className="text-xl font-bold">Acto Administrativo</h3>
                <p className="text-sm text-base-content/60">
                  Registra el acto administrativo de la etapa
                </p>
              </div>
            </div>
            <button
              onClick={() => setShowActoModal(true)}
              className="btn btn-ghost btn-sm gap-2 text-primary hover:bg-primary/10"
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
                  d="M12 4v16m8-8H4"
                />
              </svg>
              Crear
            </button>
          </div>

          <div className="bg-base-200/50 rounded-lg p-6 text-center">
            <svg
              className="w-12 h-12 text-base-content/30 mx-auto mb-3"
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
            <p className="text-base-content/60 text-sm">
              No hay acto administrativo registrado
            </p>
          </div>
        </div>

        {isEditable && (
          <ActoAdminModal
            isOpen={showActoModal}
            onClose={() => setShowActoModal(false)}
            onSave={handleSaveActoAdmin}
            editActoAdmin={null}
          />
        )}
      </div>
    );
  }

  return (
    <div className="mx-auto space-y-6">
      <ActoAdminCard
        actoAdmin={localActoAdmin as ActoAdminData}
        radicado={radicado}
        tipoActo={tipoActo}
        onEdit={() => setShowActoModal(true)}
        onDelete={() => setShowDeleteModal(true)}
        onAddComunicacion={isComunicacion ? handleAddComunicacion : undefined}
        onEditComunicacion={isComunicacion ? handleEditComunicacion : undefined}
        onComunicacionDeleted={
          isComunicacion ? handleComunicacionDeleted : undefined
        }
        onAddNotificacion={isNotificacion ? handleAddNotificacion : undefined}
        onEditNotificacion={isNotificacion ? handleEditNotificacion : undefined}
        onDeleteNotificacion={
          isNotificacion ? handleDeleteNotificacion : undefined
        }
        onViewDocument={handleViewDocument}
        involucrados={involucrados}
        tiposNotificacion={tiposNotificacion}
        setToast={setToast}
        isEditable={isEditable}
      />

      {isEditable && (
        <>
          <ActoAdminModal
            isOpen={showActoModal}
            onClose={() => setShowActoModal(false)}
            onSave={handleSaveActoAdmin}
            editActoAdmin={
              hasActoAdmin ? (localActoAdmin as ActoAdminData) : null
            }
          />

          {isComunicacion && (
            <ComunicacionModal
              isOpen={showComunicacionModal}
              onClose={() => {
                setShowComunicacionModal(false);
                setEditingComunicacion(false);
              }}
              radicado={radicado}
              actoAdminId={(localActoAdmin as ActoAdminData).id}
              idAuxiliar={idAuxiliar}
              tipoEtapa={tipoEtapa}
              editComunicacion={
                editingComunicacion && hasActoAdmin
                  ? (localActoAdmin as ActoAdminData).comunicacion || null
                  : null
              }
              onSuccess={handleComunicacionSuccess}
            />
          )}

          {isNotificacion && (
            <NotificacionModal
              isOpen={showNotificacionModal}
              onClose={() => {
                setShowNotificacionModal(false);
                setEditingNotificacion(null);
              }}
              editingNotificacion={editingNotificacion}
              involucrados={involucrados}
              yaNotificados={getYaNotificados()}
              tiposNotificacion={tiposNotificacion}
              onSave={handleSaveNotificacion}
              isEditable={isEditable}
              notificacionesExistentes={getNotificacionesExistentes()}
            />
          )}

          <ConfirmDeleteModal
            isOpen={showDeleteModal}
            onClose={() => setShowDeleteModal(false)}
            onConfirm={handleDeleteActoAdmin}
            type="acto"
            itemIdentifier={(
              localActoAdmin as ActoAdminData
            ).numerado?.toString()}
            tipoActo={tipoActo}
          />
        </>
      )}
    </div>
  );
}
