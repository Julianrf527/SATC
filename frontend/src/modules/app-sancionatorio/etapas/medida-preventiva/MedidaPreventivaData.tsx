import { useState } from "react";
import { apiCall, API_CONFIG } from "@shared/lib/api";
import CustomSelect from "@shared/ui/form/CustomSelect";
import type { Medida, SetToast, TipoCatalogo } from "../../types";
import SeccionDatos from "../comun/SeccionDatos";
import InfoItem from "../comun/InfoItem";
import SinInformacion from "../comun/SinInformacion";
import AccionesFormulario from "../comun/AccionesFormulario";
import { ICONOS } from "../comun/iconos";

type Props = {
  data?: Partial<Medida> | null;
  etapaId: number;
  expedienteId: number;
  tipoMedida: TipoCatalogo[];
  setToast: SetToast;
  isEditable?: boolean;
};

const UNIDADES = [
  { value: "m³", label: "m³" },
  { value: "L", label: "Litros" },
  { value: "m²", label: "m²" },
  { value: "Ha", label: "Hectáreas" },
  { value: "kg", label: "Kilogramos" },
  { value: "ton", label: "Toneladas" },
  { value: "und", label: "Unidades" },
  { value: "m", label: "Metros" },
  { value: "km", label: "Kilómetros" },
];

const parseCantidad = (cantidad?: string) => {
  if (!cantidad) return { valor: "", unidad: "" };
  const parts = cantidad.trim().split(" ");
  if (parts.length === 2) return { valor: parts[0], unidad: parts[1] };
  return { valor: cantidad, unidad: "" };
};

const estadoAValor = (e: boolean | null | undefined) =>
  e === null ? "null" : e?.toString() || "null";
const estadoLabel = (e: boolean | null) => (e === null ? "No Aplica" : e ? "Vigente" : "Levantada");
const estadoBadge = (e: boolean | null) =>
  e === null ? "badge-ghost" : e ? "badge-success" : "badge-warning";

export default function MedidaPreventivaData({
  data,
  etapaId,
  expedienteId,
  tipoMedida,
  setToast,
  isEditable = true,
}: Props) {
  // Hay medida registrada cuando la etapa trae el tipo de medida.
  const hasData = !!data?.id && !!data?.tipo_medida_id;
  const [medida, setMedida] = useState<Medida | null>(hasData ? (data as Medida) : null);
  const [showForm, setShowForm] = useState(isEditable && !hasData);
  const [isLoading, setIsLoading] = useState(false);
  const [tipoMedidaId, setTipoMedidaId] = useState(medida?.tipo_medida_id || 0);
  const [cantidadUnidad, setCantidadUnidad] = useState(parseCantidad(medida?.cantidad).unidad);
  const [estadoMedida, setEstadoMedida] = useState(estadoAValor(medida?.estado_medida));

  const getTipoNombre = (idTipo: number) =>
    tipoMedida.find((t) => t.id === idTipo)?.nombre || "No definido";

  const toastError = (message: string) => setToast({ id: Date.now(), message, type: "error" });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tipoMedidaId) return toastError("Seleccione el tipo de medida");
    if (!cantidadUnidad) return toastError("Seleccione la unidad de la cantidad");

    setIsLoading(true);
    try {
      const formData = new FormData(e.target as HTMLFormElement);
      const estado: boolean | null =
        estadoMedida === "true" ? true : estadoMedida === "false" ? false : null;
      const campos = {
        tipo_medida_id: tipoMedidaId,
        cantidad: `${formData.get("cantidad_valor") as string} ${cantidadUnidad}`,
        especie: (formData.get("especie") as string).trim(),
        estado_medida: estado,
      };

      // La etapa ya existe ("Crear Etapa" hace el POST): los datos siempre se guardan con PUT.
      const response = await apiCall(API_CONFIG.ENDPOINTS.FILE_MEASURE_UPDATE(expedienteId), {
        method: "PUT",
        body: JSON.stringify(campos),
      });
      if (response.ok) {
        setMedida({ id: medida?.id ?? etapaId, ...campos });
        setToast({
          id: Date.now(),
          message: medida ? "Medida actualizada exitosamente" : "Medida registrada exitosamente",
          type: "success",
        });
        setShowForm(false);
      } else {
        // apiCall ya normaliza `detail` a string (errores 422 incluidos).
        toastError(response.detail || (medida ? "Error al actualizar la medida" : "Error al registrar la medida"));
      }
    } catch {
      toastError("Error al procesar la solicitud");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SeccionDatos
      titulo="Datos de la Medida"
      icono={ICONOS.escudo}
      tono="info"
      subtitulo={
        medida
          ? "Información de la medida aplicada"
          : isEditable
            ? "Registra una nueva medida"
            : "No hay medida registrada"
      }
      onEditar={
        !showForm && medida && isEditable
          ? () => {
              setTipoMedidaId(medida.tipo_medida_id || 0);
              setCantidadUnidad(parseCantidad(medida.cantidad).unidad);
              setEstadoMedida(estadoAValor(medida.estado_medida));
              setShowForm(true);
            }
          : undefined
      }
      deshabilitado={isLoading}
    >
      {!showForm && medida && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <InfoItem icono={ICONOS.etiqueta} etiqueta="Tipo de Medida">
              <p className="text-sm font-semibold">{getTipoNombre(medida.tipo_medida_id)}</p>
            </InfoItem>
            <InfoItem icono={ICONOS.numeral} etiqueta="Cantidad">
              <p className="text-sm">{medida.cantidad}</p>
            </InfoItem>
          </div>
          <div className="space-y-4">
            <InfoItem icono={ICONOS.corazon} etiqueta="Especie">
              <p className="text-sm">{medida.especie}</p>
            </InfoItem>
            <InfoItem icono={ICONOS.checkCirculo} etiqueta="Estado de la Medida">
              <span className={`badge text-white ${estadoBadge(medida.estado_medida)} badge-sm mt-1`}>
                {estadoLabel(medida.estado_medida)}
              </span>
            </InfoItem>
          </div>
        </div>
      )}

      {!showForm && !medida && !isEditable && (
        <SinInformacion
          icono={ICONOS.escudo}
          titulo="Sin medida registrada"
          texto="No hay información de medida preventiva para este expediente"
        />
      )}

      {showForm && isEditable && (
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="flex flex-col">
              <label className="label">
                <span className="text-sm text-base-content font-medium">Tipo de Medida</span>
              </label>
              <CustomSelect
                value={tipoMedidaId}
                onChange={setTipoMedidaId}
                placeholder="Seleccione un tipo"
                disabled={isLoading}
                options={tipoMedida.map((tipo) => ({ value: tipo.id, label: tipo.nombre }))}
              />
            </div>

            <div className="flex flex-col">
              <label className="label">
                <span className="text-sm text-base-content font-medium">Cantidad</span>
              </label>
              <div className="flex gap-2">
                <input
                  type="number"
                  name="cantidad_valor"
                  defaultValue={parseCantidad(medida?.cantidad).valor}
                  className="input w-2/3"
                  placeholder="0"
                  step="0.01"
                  min="0"
                  required
                  disabled={isLoading}
                />
                <CustomSelect
                  className="w-1/3"
                  value={cantidadUnidad}
                  onChange={setCantidadUnidad}
                  emptyValue=""
                  placeholder="Unidad"
                  disabled={isLoading}
                  options={UNIDADES}
                />
              </div>
            </div>

            <div className="flex flex-col">
              <label className="label">
                <span className="text-sm text-base-content font-medium">Especie</span>
              </label>
              <input
                type="text"
                name="especie"
                defaultValue={medida?.especie || ""}
                className="input w-full"
                required
                disabled={isLoading}
              />
            </div>

            <div className="flex flex-col">
              <label className="label">
                <span className="text-sm text-base-content font-medium">Estado de la Medida</span>
              </label>
              <CustomSelect
                hidePlaceholderOption
                value={estadoMedida}
                onChange={setEstadoMedida}
                disabled={isLoading}
                options={[
                  { value: "true", label: "Vigente" },
                  { value: "false", label: "Levantada" },
                  { value: "null", label: "No Aplica" },
                ]}
              />
            </div>
          </div>

          <AccionesFormulario
            onCancelar={medida ? () => setShowForm(false) : undefined}
            textoGuardar={medida ? "Guardar Cambios" : "Registrar Medida"}
            tono="info"
            guardando={isLoading}
          />
        </form>
      )}
    </SeccionDatos>
  );
}
