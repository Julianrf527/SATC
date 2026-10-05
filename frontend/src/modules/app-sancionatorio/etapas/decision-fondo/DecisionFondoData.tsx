import { useState } from "react";
import { apiCall, API_CONFIG } from "@shared/lib/api";
import CustomSelect from "@shared/ui/form/CustomSelect";
import type { Decision, SetToast, TipoCatalogo } from "../../types";
import SeccionDatos from "../comun/SeccionDatos";
import InfoItem from "../comun/InfoItem";
import SinInformacion from "../comun/SinInformacion";
import AccionesFormulario from "../comun/AccionesFormulario";
import { ICONOS } from "../comun/iconos";

type Props = {
  data: Decision | null | undefined;
  tipoSancion: TipoCatalogo[];
  setToast: SetToast;
  expedienteId: number;
  onDataUpdated?: () => void;
  isEditable?: boolean;
};

export default function DecisionFondoData({
  data,
  tipoSancion,
  setToast,
  expedienteId,
  onDataUpdated,
  isEditable = true,
}: Props) {
  const [showForm, setShowForm] = useState(!data && isEditable);
  const [isLoading, setIsLoading] = useState(false);
  const [tipoSancionId, setTipoSancionId] = useState(data?.tipo_sancion_id || 0);

  const getTipoNombre = (idTipo: number) =>
    tipoSancion.find((t) => t.id === idTipo)?.nombre || "No definido";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tipoSancionId) {
      setToast({ id: Date.now(), message: "Seleccione un tipo de sanción", type: "error" });
      return;
    }
    setIsLoading(true);

    try {
      const formData = new FormData(e.target as HTMLFormElement);
      // La etapa ya existe ("Crear Etapa" hace el POST): los datos siempre se guardan con PUT.
      const res = await apiCall(API_CONFIG.ENDPOINTS.FILE_DECISION_UPDATE(expedienteId), {
        method: "PUT",
        body: JSON.stringify({
          tipo_sancion_id: tipoSancionId,
          detalle: (formData.get("detalle") as string).trim(),
        }),
      });

      if (res.ok) {
        setToast({
          id: Date.now(),
          message: data?.id ? "Decisión actualizada" : "Decisión registrada",
          type: "success",
        });
        setShowForm(false);
        onDataUpdated?.();
      } else {
        setToast({ id: Date.now(), message: res.detail || "Error al guardar", type: "error" });
      }
    } catch {
      setToast({ id: Date.now(), message: "Error al procesar la solicitud", type: "error" });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SeccionDatos
      titulo="Decisión de Fondo"
      icono={ICONOS.checkCirculo}
      tono="error"
      subtitulo={
        data
          ? "Información de la decisión de fondo"
          : isEditable
            ? "Registra una nueva decisión"
            : "No hay decisión registrada"
      }
      onEditar={
        !showForm && data && isEditable
          ? () => {
              setTipoSancionId(data.tipo_sancion_id || 0);
              setShowForm(true);
            }
          : undefined
      }
      deshabilitado={isLoading}
    >
      {!showForm && data && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <InfoItem icono={ICONOS.alerta} etiqueta="Tipo de Sanción">
              <p className="text-sm font-semibold">{getTipoNombre(data.tipo_sancion_id)}</p>
            </InfoItem>
          </div>
          <div className="space-y-4">
            <InfoItem icono={ICONOS.documento} etiqueta="Detalle de la Decisión" className="flex-1">
              <p className="text-sm mt-1">{data.detalle}</p>
            </InfoItem>
          </div>
        </div>
      )}

      {!showForm && !data && !isEditable && (
        <SinInformacion
          punteado
          icono={ICONOS.documento}
          titulo="Sin decisión registrada"
          texto="No hay información de decisión de fondo para este expediente"
        />
      )}

      {showForm && isEditable && (
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 gap-6">
            <div className="flex flex-col">
              <label className="label">
                <span className="text-sm text-base-content font-medium">Tipo de Sanción</span>
              </label>
              <CustomSelect
                value={tipoSancionId}
                onChange={setTipoSancionId}
                placeholder="Seleccione un tipo"
                disabled={isLoading}
                options={tipoSancion.map((tipo) => ({ value: tipo.id, label: tipo.nombre }))}
              />
            </div>

            <div className="flex flex-col">
              <label className="label">
                <span className="text-sm text-base-content font-medium">Detalle de la Decisión</span>
              </label>
              <textarea
                name="detalle"
                defaultValue={data?.detalle || ""}
                className="textarea w-full h-24"
                placeholder="Describa la decisión tomada..."
                required
                disabled={isLoading}
              />
            </div>
          </div>

          <AccionesFormulario
            onCancelar={data ? () => setShowForm(false) : undefined}
            textoGuardar={data ? "Guardar Cambios" : "Registrar Decisión"}
            tono="error"
            guardando={isLoading}
          />
        </form>
      )}
    </SeccionDatos>
  );
}
