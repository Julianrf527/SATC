import { useEffect, useState } from "react";
import { apiCall, API_CONFIG, getErrorMessage } from "../../../utils/api";
import { uploadFileToDocuments, validateFile } from "../../../utils/fileUpload";
import { useAuth } from "../../../context/AuthContext";
import { openDocumentById } from "../../../utils/documentViewer";
import type { InformeTecnico, ProfesionalDisponible } from "../../../types/infraccionApp";
import CustomDateInput from "../../Common/Form/CustomDateInput";
import CustomSelect from "../../Common/Form/CustomSelect";

const PERMISO_CARGUE = "infraccion_cargue";

type Props = {
  informe: InformeTecnico;
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  onUpdated: () => void;
  isEditable: boolean;
};

export default function CargueManualInforme({
  informe,
  setToast,
  onUpdated,
  isEditable,
}: Props) {
  const { user } = useAuth();
  const tieneCarguePermiso =
    isEditable &&
    (user?.permisos ?? []).some((p) => p.name === PERMISO_CARGUE);

  const [confirmModo, setConfirmModo] = useState<"FLUJO" | "MANUAL" | null>(
    null,
  );
  const [switching, setSwitching] = useState(false);
  const [editando, setEditando] = useState(false);

  const [archivo, setArchivo] = useState<File | null>(null);
  const [fechaRecibido, setFechaRecibido] = useState("");
  const [fechaAceptacion, setFechaAceptacion] = useState("");
  const [fechaProgramacion, setFechaProgramacion] = useState("");
  const [profesionalId, setProfesionalId] = useState<number | "">("");
  const [revisorId, setRevisorId] = useState<number | "">("");
  const [profesionales, setProfesionales] = useState<ProfesionalDisponible[]>([]);
  const [revisores, setRevisores] = useState<ProfesionalDisponible[]>([]);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    if (informe.modo !== "MANUAL" || !tieneCarguePermiso) return;
    apiCall(API_CONFIG.ENDPOINTS.INFRACTION_REPORTS_DISPONIBLES, { method: "GET" })
      .then((res) => {
        if (res.ok) {
          setProfesionales(res.profesionales_disponibles || []);
          setRevisores(res.revisores_disponibles || []);
        }
      })
      .catch(() => {});
  }, [informe.modo, tieneCarguePermiso]);

  useEffect(() => {
    setProfesionalId(informe.profesional_asignado_id ?? "");
    setRevisorId(informe.revisor_asignado_id ?? "");
    setFechaRecibido(informe.fecha_recibido_informe ?? "");
    setFechaAceptacion(informe.fecha_aceptacion_informe ?? "");
    setFechaProgramacion(informe.fecha_programacion_visita ?? "");
    setArchivo(null);
  }, [
    informe.id,
    informe.profesional_asignado_id,
    informe.revisor_asignado_id,
    informe.fecha_recibido_informe,
    informe.fecha_aceptacion_informe,
    informe.fecha_programacion_visita,
  ]);

  const handleSwitchMode = async () => {
    if (!confirmModo) return;
    setSwitching(true);
    try {
      const res = await apiCall(
        API_CONFIG.ENDPOINTS.INFRACTION_REPORTS_SWITCH_MODE(informe.id),
        { method: "PUT", body: JSON.stringify({ modo: confirmModo }) },
      );
      if (res.ok) {
        setToast({
          id: Date.now(),
          message:
            confirmModo === "MANUAL"
              ? "Cambiado a cargue manual"
              : "Cambiado a flujo normal",
          type: "success",
        });
        onUpdated();
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al cambiar el modo",
          type: "error",
        });
      }
    } catch (e) {
      setToast({
        id: Date.now(),
        message: getErrorMessage(e, "Error al cambiar el modo"),
        type: "error",
      });
    } finally {
      setSwitching(false);
      setConfirmModo(null);
    }
  };

  const handleManualSubmit = async () => {
    if (!archivo && !informe.documento_informe_id) {
      setToast({ id: Date.now(), message: "Selecciona un archivo", type: "error" });
      return;
    }
    if (archivo) {
      const validacion = validateFile(archivo, [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      ]);
      if (!validacion.isValid) {
        setToast({ id: Date.now(), message: validacion.error!, type: "error" });
        return;
      }
    }
    if (!fechaRecibido || !fechaAceptacion) {
      setToast({
        id: Date.now(),
        message: "Completa la fecha de recibido y de aceptación",
        type: "error",
      });
      return;
    }

    setUploading(true);
    try {
      const fileId = archivo
        ? await uploadFileToDocuments(archivo, archivo.name)
        : informe.documento_informe_id!;
      const res = await apiCall(
        API_CONFIG.ENDPOINTS.INFRACTION_REPORTS_MANUAL_UPLOAD(informe.id),
        {
          method: "POST",
          body: JSON.stringify({
            file_id: fileId,
            fecha_recibido: fechaRecibido,
            fecha_aceptacion: fechaAceptacion,
            ...(fechaProgramacion
              ? { fecha_programacion_visita: fechaProgramacion }
              : {}),
            ...(profesionalId ? { profesional_id: profesionalId } : {}),
            ...(revisorId ? { revisor_id: revisorId } : {}),
          }),
        },
      );
      if (res.ok) {
        setToast({
          id: Date.now(),
          message: informe.documento_informe_id
            ? "Informe actualizado correctamente"
            : "Informe cargado y aceptado correctamente",
          type: "success",
        });
        setEditando(false);
        onUpdated();
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al cargar el informe",
          type: "error",
        });
      }
    } catch (e) {
      setToast({
        id: Date.now(),
        message: getErrorMessage(e, "Error al cargar el informe"),
        type: "error",
      });
    } finally {
      setUploading(false);
    }
  };

  if (!tieneCarguePermiso) {
    return null;
  }

  return (
    <div className="card bg-base-200/50 border border-base-300">
      <div className="card-body space-y-4 p-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <p className="text-sm text-base-content/70">
            Modo de cargue:{" "}
            <span className="font-semibold text-base-content">
              {informe.modo === "MANUAL" ? "Manual" : "Flujo normal"}
            </span>
          </p>
          <button
            className="btn btn-sm btn-ghost gap-2"
            onClick={() =>
              setConfirmModo(informe.modo === "MANUAL" ? "FLUJO" : "MANUAL")
            }
            disabled={switching}
          >
            Cambiar a {informe.modo === "MANUAL" ? "flujo normal" : "cargue manual"}
          </button>
        </div>

        {informe.modo === "MANUAL" && informe.documento_informe_id && !editando && (
          <div className="flex items-center justify-between gap-3 p-3 bg-base-100 rounded-lg border border-base-300">
            <div className="flex items-center gap-3">
              <svg className="w-4 h-4 text-success flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <p className="text-sm text-base-content/70">
                Informe cargado manualmente el {informe.fecha_aceptacion_informe}.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => openDocumentById(informe.documento_informe_id!)}
                className="btn btn-ghost btn-xs gap-1 text-success"
              >
                Ver archivo
              </button>
              <button
                onClick={() => setEditando(true)}
                className="btn btn-outline btn-xs gap-1"
              >
                Editar
              </button>
            </div>
          </div>
        )}

        {informe.modo === "MANUAL" && (!informe.documento_informe_id || editando) && (
          <div className="space-y-4">
            <p className="text-sm text-gray-500">
              Cargue directo de un informe ya aceptado previamente fuera del
              sistema (expedientes históricos). No pasa por asignación ni
              revisión.
            </p>

            <div className="form-control">
              <label className="label py-1">
                <span className="label-text font-medium">
                  Archivo{" "}
                  {!informe.documento_informe_id && <span className="text-error">*</span>}
                  {informe.documento_informe_id && (
                    <span className="text-base-content/40 text-xs font-normal ml-1">
                      (Opcional — deja vacío para mantener el actual)
                    </span>
                  )}
                </span>
              </label>
              {informe.documento_informe_id && (
                <button
                  type="button"
                  onClick={() => openDocumentById(informe.documento_informe_id!)}
                  className="btn btn-ghost btn-xs gap-1 text-success w-fit mb-1"
                >
                  Ver archivo actual
                </button>
              )}
              <input
                type="file"
                accept=".pdf,.doc,.docx"
                className="file-input file-input-bordered w-full"
                onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
                disabled={uploading}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="form-control">
                <label className="label py-1">
                  <span className="label-text font-medium">
                    Fecha de Recibido <span className="text-error">*</span>
                  </span>
                </label>
                <CustomDateInput
                  value={fechaRecibido}
                  onChange={setFechaRecibido}
                  max={new Date().toISOString().split("T")[0]}
                  disabled={uploading}
                />
              </div>
              <div className="form-control">
                <label className="label py-1">
                  <span className="label-text font-medium">
                    Fecha de Aceptación <span className="text-error">*</span>
                  </span>
                </label>
                <CustomDateInput
                  value={fechaAceptacion}
                  onChange={setFechaAceptacion}
                  max={new Date().toISOString().split("T")[0]}
                  disabled={uploading}
                />
              </div>
              <div className="form-control">
                <label className="label py-1">
                  <span className="label-text font-medium">
                    Fecha de Programación de Visita
                    <span className="text-base-content/40 text-xs font-normal ml-1">
                      (Opcional)
                    </span>
                  </span>
                </label>
                <CustomDateInput
                  value={fechaProgramacion}
                  onChange={setFechaProgramacion}
                  max={new Date().toISOString().split("T")[0]}
                  disabled={uploading}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="form-control">
                <label className="label py-1">
                  <span className="label-text font-medium">
                    Profesional que cargó
                    <span className="text-base-content/40 text-xs font-normal ml-1">
                      (Opcional)
                    </span>
                  </span>
                </label>
                <CustomSelect
                  value={profesionalId === "" ? 0 : profesionalId}
                  onChange={(v) => setProfesionalId(v === 0 ? "" : v)}
                  placeholder="Sin asignar"
                  disabled={uploading}
                  options={profesionales.map((p) => ({ value: p.id, label: p.nombre }))}
                />
              </div>
              <div className="form-control">
                <label className="label py-1">
                  <span className="label-text font-medium">
                    Revisor
                    <span className="text-base-content/40 text-xs font-normal ml-1">
                      (Opcional)
                    </span>
                  </span>
                </label>
                <CustomSelect
                  value={revisorId === "" ? 0 : revisorId}
                  onChange={(v) => setRevisorId(v === 0 ? "" : v)}
                  placeholder="Sin asignar"
                  disabled={uploading}
                  options={revisores.map((r) => ({ value: r.id, label: r.nombre }))}
                />
              </div>
            </div>

            <div className="flex justify-end gap-2">
              {editando && (
                <button
                  className="btn btn-ghost"
                  onClick={() => setEditando(false)}
                  disabled={uploading}
                >
                  Cancelar
                </button>
              )}
              <button
                className="btn btn-success text-white gap-2"
                onClick={handleManualSubmit}
                disabled={uploading}
              >
                {uploading ? (
                  <>
                    <span className="loading loading-spinner loading-xs" />
                    Guardando...
                  </>
                ) : informe.documento_informe_id ? (
                  "Guardar cambios"
                ) : (
                  "Cargar informe"
                )}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modal de confirmación al cambiar de modo */}
      {confirmModo && (
        <div
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50 backdrop-blur-sm"
          onClick={() => !switching && setConfirmModo(null)}
        >
          <div
            className="bg-base-100 rounded-xl w-full max-w-md mx-4 shadow-2xl border border-base-300 p-6 space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="font-bold text-base text-base-content">
              Cambiar a {confirmModo === "MANUAL" ? "cargue manual" : "flujo normal"}
            </h3>
            <p className="text-sm text-base-content/70">
              Esto eliminará por completo la información del modo actual
              (archivo, fechas{informe.modo === "FLUJO" ? ", profesional y revisor" : ""}
              ). Esta acción no se puede deshacer. ¿Continuar?
            </p>
            <div className="flex justify-end gap-2">
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => setConfirmModo(null)}
                disabled={switching}
              >
                Cancelar
              </button>
              <button
                className="btn btn-warning btn-sm text-white"
                onClick={handleSwitchMode}
                disabled={switching}
              >
                {switching ? (
                  <span className="loading loading-spinner loading-xs" />
                ) : (
                  "Sí, cambiar"
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
