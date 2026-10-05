import { useState, useEffect } from "react";
import { ApiError } from "@shared/lib/api";
import type { ExpedienteDetalle } from "@shared/types/sancionatorio";
import type { Municipio, ModeloGenerico } from "@shared/types/common";
import { useActualizarDatosBasicosMutation } from "../../api/expediente";
import type { SetToast } from "../../types";
import Icono from "../comun/Icono";
import { ICONOS } from "../comun/iconos";
import InformacionExpedienteView from "./InformacionExpedienteView";
import InformacionExpedienteForm from "./InformacionExpedienteForm";

interface Props {
  expediente: ExpedienteDetalle;
  municipioList: Municipio[];
  recursoAfectadoList: ModeloGenerico[];
  onUpdate?: (expediente: ExpedienteDetalle) => void;
  setToast: SetToast;
  isEditable?: boolean;
}

export default function InformacionExpedienteData({
  expediente,
  municipioList,
  recursoAfectadoList,
  onUpdate,
  setToast,
  isEditable = true,
}: Props) {
  const [showForm, setShowForm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [recursosSeleccionados, setRecursosSeleccionados] = useState<number[]>(
    expediente.recurso_afectado || [],
  );
  const [veredaList, setVeredaList] = useState<ModeloGenerico[]>([]);
  const [municipioId, setMunicipioId] = useState(expediente.municipio?.id || 0);
  const [veredaId, setVeredaId] = useState(expediente.vereda?.id || 0);
  const actualizar = useActualizarDatosBasicosMutation(expediente.id);

  useEffect(() => {
    const town = municipioList.find((t) => t.veredas.some((s) => s.id === expediente.vereda?.id));
    setVeredaList(town?.veredas || []);
  }, [expediente, municipioList]);

  const toastError = (message: string) => setToast({ id: Date.now(), message, type: "error" });

  const toggleChangeTown = (townId: number) => {
    setMunicipioId(townId);
    setVeredaId(0);
    setVeredaList(municipioList.find((t) => t.id === townId)?.veredas || []);
  };

  const validateForm = () => {
    const error = !municipioId
      ? "Debe seleccionar un municipio"
      : !veredaId
        ? "Debe seleccionar una vereda"
        : recursosSeleccionados.length === 0
          ? "Debe seleccionar al menos un recurso afectado"
          : null;
    if (error) toastError(error);
    return !error;
  };

  const hasDataChanged = (formData: FormData): boolean => {
    const resourcesChanged =
      JSON.stringify([...recursosSeleccionados].sort()) !==
      JSON.stringify([...(expediente.recurso_afectado || [])].sort());
    return (
      formData.get("radicado") !== expediente.radicado ||
      formData.get("nombre") !== expediente.expediente ||
      formData.get("motivo") !== (expediente.motivo_afectacion || "") ||
      formData.get("direccion") !== expediente.direccion ||
      veredaId !== (expediente.vereda?.id || 0) ||
      municipioId !== expediente.municipio.id ||
      resourcesChanged
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const formData = new FormData(e.target as HTMLFormElement);
    if (!validateForm()) return;
    if (!hasDataChanged(formData)) {
      setShowForm(false);
      return;
    }

    setIsLoading(true);
    const texto = (campo: string) => (formData.get(campo) as string).trim();
    const updated: ExpedienteDetalle = {
      ...expediente,
      radicado: texto("radicado"),
      expediente: texto("nombre"),
      recurso_afectado: recursosSeleccionados,
      motivo_afectacion: texto("motivo"),
      direccion: texto("direccion"),
      vereda: { id: veredaId, nombre: veredaList.find((s) => s.id === veredaId)?.nombre || "" },
      municipio: {
        id: municipioId,
        nombre: municipioList.find((t) => t.id === municipioId)?.nombre || expediente.municipio.nombre,
      },
    };

    try {
      await actualizar.mutateAsync({
        radicado: updated.radicado,
        expediente: updated.expediente,
        recurso: updated.recurso_afectado || [],
        motivo: updated.motivo_afectacion || "",
        vereda: updated.vereda?.id || 0,
        direccion: updated.direccion,
      });
      setToast({ id: Date.now(), message: "Expediente actualizado exitosamente", type: "success" });
      // Margen para que el servidor procese antes de que el padre refresque
      await new Promise((resolve) => setTimeout(resolve, 300));
      onUpdate?.(updated);
      setRecursosSeleccionados(updated.recurso_afectado || []);
      setShowForm(false);
    } catch (error) {
      if (error instanceof ApiError) {
        const detalle = error.data?.detail;
        toastError(typeof detalle === "string" && detalle ? detalle : "El radicado se encuentra en uso");
      } else {
        toastError("Error de conexión al actualizar el expediente");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setRecursosSeleccionados(expediente.recurso_afectado || []);
    setMunicipioId(expediente.municipio?.id || 0);
    setVeredaId(expediente.vereda?.id || 0);
    setShowForm(false);
  };

  return (
    <div className="card bg-base-100 shadow border border-base-300">
      <div className="card-body p-0">
        <div className="px-5 py-4 border-b border-base-200 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-success/10 rounded-lg flex items-center justify-center flex-shrink-0">
              <Icono d={ICONOS.documento} className="w-4 h-4 text-success" />
            </div>
            <div>
              <p className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wider">Expediente</p>
              <h2 className="text-base font-bold text-base-content">Datos del Expediente</h2>
            </div>
          </div>
          {!showForm && isEditable && (
            <button
              className="btn btn-ghost btn-sm gap-2 text-success hover:bg-success/10"
              onClick={() => {
                setMunicipioId(expediente.municipio?.id || 0);
                setVeredaId(expediente.vereda?.id || 0);
                setShowForm(true);
              }}
              disabled={isLoading}
            >
              <Icono d={ICONOS.editar} />
              Editar
            </button>
          )}
        </div>
        <div className="p-5">
          {!showForm && (
            <InformacionExpedienteView expediente={expediente} recursoAfectadoList={recursoAfectadoList} />
          )}

          {showForm && isEditable && (
            <InformacionExpedienteForm
              expediente={expediente}
              municipioList={municipioList}
              veredaList={veredaList}
              recursoAfectadoList={recursoAfectadoList}
              municipioId={municipioId}
              veredaId={veredaId}
              recursosSeleccionados={recursosSeleccionados}
              onMunicipioChange={toggleChangeTown}
              onVeredaChange={setVeredaId}
              onRecursoToggle={(id) =>
                setRecursosSeleccionados((prev) =>
                  prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id],
                )
              }
              onSubmit={handleSubmit}
              onCancel={handleCancel}
              isLoading={isLoading}
            />
          )}
        </div>
      </div>
    </div>
  );
}
