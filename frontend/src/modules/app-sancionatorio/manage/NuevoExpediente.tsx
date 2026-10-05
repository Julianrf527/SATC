import { useRef, useState, type FormEvent } from "react";
import { apiCall, API_CONFIG } from "@shared/lib/api";
import { Campo } from "@shared/ui/form/Campo";
import type { Municipio, ModeloGenerico } from "@shared/types/common";
import type { Expediente, ExpedienteDetalle } from "@shared/types/sancionatorio";
import {
  CampoTexto,
  NuevoExpedienteLayout,
  RADICADO_PATTERN,
  RADICADO_TITLE,
  UbicacionFields,
  useUbicacion,
  type SetToast,
} from "@features/expedientes";

type Props = {
  userId: number;
  municipioList: Municipio[];
  recursoAfectadoList: ModeloGenerico[];
  setToast: SetToast;
  onCancel: () => void;
  addExpediente: (expediente: Expediente) => void;
};

/**
 * Alta de expediente sancionatorio. Usa el armazón y la ubicación comunes de
 * `@features/expedientes`; número de expediente, recursos (sin tipos) y motivo
 * son propios de este flujo.
 */
export default function NuevoExpediente({
  userId,
  municipioList,
  recursoAfectadoList,
  setToast,
  onCancel,
  addExpediente,
}: Props) {
  const ubicacion = useUbicacion(municipioList);
  const [errorMsg, setErrorMsg] = useState("");
  const [recursosSeleccionados, setRecursosSeleccionados] = useState<number[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const formRef = useRef<HTMLFormElement | null>(null);

  const resetForm = () => {
    formRef.current?.reset();
    ubicacion.reset();
    setRecursosSeleccionados([]);
    setErrorMsg("");
  };

  const handleResourceToggle = (id: number) =>
    setRecursosSeleccionados((prev) =>
      prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id],
    );

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);

    if (!ubicacion.municipioId) return setErrorMsg("Seleccione un municipio");
    if (!ubicacion.veredaId) return setErrorMsg("Seleccione una vereda");
    if (recursosSeleccionados.length === 0) {
      return setErrorMsg("Seleccione al menos un recurso afectado");
    }
    setErrorMsg("");

    const data = {
      radicado: formData.get("radicado"),
      expediente: formData.get("expediente"),
      recurso: recursosSeleccionados,
      motivo: formData.get("motivo"),
      encargado_id: userId,
      municipio: String(ubicacion.municipioId),
      vereda: String(ubicacion.veredaId),
      direccion: formData.get("direccion"),
    };

    setIsSubmitting(true);
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.FILE_ADD, {
        method: "POST",
        body: JSON.stringify(data),
      });
      if (!res.ok) {
        setErrorMsg(res.detail || "Error al registrar el expediente");
        return;
      }
      const expedienteId = res.expediente_id ?? res.data?.expediente_id;
      if (!expedienteId) {
        setErrorMsg("Error al registrar el expediente");
        return;
      }
      setToast({ id: Date.now(), message: "Expediente registrado", type: "success" });

      const { municipio, vereda } = ubicacion;
      const nuevoExpediente: ExpedienteDetalle = {
        id: expedienteId,
        radicado: String(data.radicado ?? ""),
        expediente: String(data.expediente ?? ""),
        fecha_creacion: new Date().toISOString().split("T")[0],
        direccion: String(data.direccion ?? ""),
        municipio: municipio
          ? { id: municipio.id, nombre: municipio.nombre }
          : { id: 0, nombre: "Desconocido" },
        involucrados: [],
        archivado: false,
        vereda: vereda ? { id: vereda.id, nombre: vereda.nombre } : { id: 0, nombre: "Desconocido" },
        recurso_afectado: recursosSeleccionados,
        motivo_afectacion: String(data.motivo ?? ""),
      };
      addExpediente(nuevoExpediente);

      resetForm();
      onCancel();
    } catch {
      setErrorMsg("Error de conexión con el servidor");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelClick = () => {
    resetForm();
    onCancel();
  };

  return (
    <NuevoExpedienteLayout
      formId="new-file-form"
      formRef={formRef}
      onSubmit={handleSubmit}
      onCancelar={handleCancelClick}
      isSubmitting={isSubmitting}
      errorGeneral={errorMsg && recursosSeleccionados.length > 0 ? errorMsg : null}
    >
      <CampoTexto
        etiqueta="Radicado *"
        name="radicado"
        placeholder="Ingrese el radicado"
        required
        disabled={isSubmitting}
        pattern={RADICADO_PATTERN}
        title={RADICADO_TITLE}
      />

      <CampoTexto
        etiqueta="Numero del Expediente *"
        name="expediente"
        placeholder="Numero del expediente"
        required
        disabled={isSubmitting}
        pattern="^Q\d{3}-\d{2}$"
        title="Debe tener el formato: Q + 3 números + - + 2 números (ej: Q123-45)"
      />

      <Campo
        etiqueta="Recursos Afectados *"
        error={errorMsg && recursosSeleccionados.length === 0 ? errorMsg : null}
      >
        <div className="bg-base-200 rounded-lg p-4 border border-base-300">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {recursoAfectadoList.map((r) => (
              <label
                key={r.id}
                className="flex items-center gap-3 p-3 bg-base-100 rounded-lg border border-base-300 hover:border-success cursor-pointer transition-colors"
              >
                <input
                  type="checkbox"
                  value={r.id}
                  checked={recursosSeleccionados.includes(r.id)}
                  onChange={() => handleResourceToggle(r.id)}
                  className="checkbox checkbox-success checkbox-white-check checkbox-sm"
                  disabled={isSubmitting}
                />
                <span className="text-sm font-medium text-base-content">{r.nombre}</span>
              </label>
            ))}
          </div>
        </div>
      </Campo>

      <Campo etiqueta="Motivo de Afectación *">
        <textarea
          name="motivo"
          placeholder="Describa el motivo de la afectación"
          className="textarea w-full h-24 resize-none"
          required
          disabled={isSubmitting}
          maxLength={200}
        />
      </Campo>

      <UbicacionFields municipioList={municipioList} ubicacion={ubicacion} disabled={isSubmitting} />
    </NuevoExpedienteLayout>
  );
}
