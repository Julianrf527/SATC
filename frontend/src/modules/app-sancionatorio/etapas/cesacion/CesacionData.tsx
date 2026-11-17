import { useState } from "react";
import { apiCall, API_CONFIG } from "@shared/lib/api";
import CustomSelect from "@shared/ui/form/CustomSelect";
import type { Cesacion, SetToast, TipoCatalogo } from "../../types";
import SeccionDatos from "../comun/SeccionDatos";
import InfoItem from "../comun/InfoItem";
import SinInformacion from "../comun/SinInformacion";
import AccionesFormulario from "../comun/AccionesFormulario";
import { ICONOS } from "../comun/iconos";

type Props = {
  data?: Partial<Cesacion> | null;
  tipoMedida: TipoCatalogo[];
  setToast: SetToast;
  etapaId: number;
  expedienteId: number;
  onDataUpdated?: () => void;
  isEditable?: boolean;
};

export default function CesacionData({
  data,
  tipoMedida,
  setToast,
  etapaId,
  expedienteId,
  onDataUpdated,
  isEditable = true,
}: Props) {
  // Hay cesación registrada cuando la etapa trae el tipo de cesación.
  const hasCesacion = !!data?.id && !!data?.tipo_cesacion_id;
  const [localData, setLocalData] = useState<Cesacion | null>(
    hasCesacion ? (data as Cesacion) : null,
  );
  const [showForm, setShowForm] = useState(!hasCesacion && isEditable);
  const [isLoading, setIsLoading] = useState(false);
  const [tipoCesacionId, setTipoCesacionId] = useState(localData?.tipo_cesacion_id || 0);

  const getTipoNombre = (idTipo: number) =>
    tipoMedida.find((t) => t.id === idTipo)?.nombre || "No definido";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tipoCesacionId) {
      setToast({ id: Date.now(), message: "Seleccione un tipo de cesación", type: "error" });
      return;
    }
    setIsLoading(true);

    try {
      // La etapa ya existe ("Crear Etapa" hace el POST): los datos siempre se guardan con PUT.
      const res = await apiCall(API_CONFIG.ENDPOINTS.FILE_CESSATION_UPDATE(expedienteId), {
        method: "PUT",
        body: JSON.stringify({ tipo_cesacion_id: tipoCesacionId }),
      });

      if (res.ok) {
        setLocalData({ id: localData?.id ?? etapaId, tipo_cesacion_id: tipoCesacionId });
        setToast({
          id: Date.now(),
          message: res.message || (localData?.id ? "Cesación actualizada" : "Cesación registrada"),
          type: "success",
        });
        setShowForm(false);
        onDataUpdated?.();
      } else {
        setToast({ id: Date.now(), message: res.detail || res.message || "Error al guardar", type: "error" });
      }
    } catch {
      setToast({ id: Date.now(), message: "Error al procesar la solicitud", type: "error" });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SeccionDatos
      titulo="Tipo de Cesación"
      icono={ICONOS.documento}
      tono="info"
      subtitulo={
        localData
          ? "Información del tipo de cesación aplicada"
          : isEditable
            ? "Registra el tipo de cesación"
            : "No hay cesación registrada"
      }
      onEditar={
        !showForm && localData && isEditable
          ? () => {
              setTipoCesacionId(localData.tipo_cesacion_id || 0);
              setShowForm(true);
            }
          : undefined
      }
      deshabilitado={isLoading}
    >
      {!showForm && localData && (
        <div className="space-y-4">
          <InfoItem icono={ICONOS.etiqueta} etiqueta="Tipo de Cesación">
            <p className="text-sm font-semibold mt-1">{getTipoNombre(localData.tipo_cesacion_id)}</p>
          </InfoItem>
        </div>
      )}

      {!showForm && !localData && !isEditable && (
        <SinInformacion
          icono={ICONOS.documento}
          titulo="Sin cesación registrada"
          texto="No hay información de tipo de cesación para este expediente"
        />
      )}

      {showForm && isEditable && (
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="flex flex-col">
            <label className="label">
              <span className="text-sm text-base-content font-medium">
                Tipo de Cesación <span className="text-error">*</span>
              </span>
            </label>
            <CustomSelect
              value={tipoCesacionId}
              onChange={setTipoCesacionId}
              placeholder="Seleccione un tipo"
              disabled={isLoading}
              options={tipoMedida.map((tipo) => ({ value: tipo.id, label: tipo.nombre }))}
            />
          </div>

          <AccionesFormulario
            onCancelar={localData ? () => setShowForm(false) : undefined}
            textoGuardar={localData ? "Guardar Cambios" : "Registrar Cesación"}
            tono="info"
            guardando={isLoading}
          />
        </form>
      )}
    </SeccionDatos>
  );
}
